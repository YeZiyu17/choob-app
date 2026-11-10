(() => {
  const leafBase = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/';
  const loadTimeout = 8000;
  let configRequest;
  let leafletRequest;
  let leafletStyle;
  let googleRequest;
  let googleAuthFailed;

  function loadAsset(tag, properties) {
    return new Promise((resolve, reject) => {
      const element = Object.assign(document.createElement(tag), properties);
      const finish = success => {
        clearTimeout(timer);
        element.onload = element.onerror = null;
        if (success) {
          resolve();
        } else {
          element.remove();
          reject(new Error('Map assets could not be loaded'));
        }
      };
      const timer = setTimeout(() => finish(false), loadTimeout);
      element.onload = () => finish(true);
      element.onerror = () => finish(false);
      document.head.append(element);
    });
  }

  function mapConfig() {
    configRequest ??= fetch('/api/passport-map-config', {signal: AbortSignal.timeout?.(3000)})
      .then(response => response.ok ? response.json() : {})
      .catch(() => ({}));
    return configRequest;
  }

  function loadLeaflet() {
    leafletStyle ??= loadAsset('link', {
      rel: 'stylesheet',
      href: leafBase + 'leaflet.css',
      crossOrigin: 'anonymous',
      integrity: 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=',
    }).catch(error => {
      leafletStyle = undefined;
      throw error;
    });
    leafletRequest ??= Promise.all([
      leafletStyle,
      window.L || loadAsset('script', {
        src: leafBase + 'leaflet.js',
        crossOrigin: 'anonymous',
        integrity: 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=',
      }),
    ]).then(() => window.L).catch(error => {
      leafletRequest = undefined;
      throw error;
    });
    return leafletRequest;
  }

  function pinContent(symbol, saved) {
    const pin = document.createElement('span');
    pin.className = saved ? 'passport-map-pin passport-map-pin-saved' : 'passport-map-pin passport-map-pin-preview';
    pin.setAttribute('aria-hidden', 'true');
    pin.textContent = symbol;
    return pin;
  }

  async function createLeaflet(container, {center, zoom, onPick, onStatus}) {
    const L = await loadLeaflet();
    container.classList.add('passport-map-leaflet');
    const map = L.map(container, {
      scrollWheelZoom: false, worldCopyJump: true, maxZoom: 19, zoomControl: false,
    }).setView(center, zoom);
    map.attributionControl.setPrefix(false).setPosition('bottomleft');
    const zoomControl = L.control.zoom({position: 'bottomright'}).addTo(map);
    zoomControl.getContainer().classList.add('passport-map-zoom');
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      className: 'passport-map-tiles',
      maxZoom: 19,
      opacity: onPick ? 1 : 0.68,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    });
    let tileFailed = false;
    tiles.on('loading', () => { tileFailed = false; });
    tiles.on('tileerror', () => { tileFailed = true; });
    tiles.on('load', () => onStatus?.(tileFailed ? 'Some map tiles could not load.' : ''));
    tiles.addTo(map);
    const layer = L.layerGroup().addTo(map);
    if (onPick) {
      map.on('click', ({latlng}) => {
        const {lat, lng} = latlng.wrap();
        onPick({lat, lng});
      });
    }
    return {
      setMarkers(markers) {
        layer.clearLayers();
        for (const {lat, lng, symbol, label, onClick} of markers) {
          const saved = Boolean(onClick);
          const marker = L.marker([lat, lng], {
            title: label,
            interactive: saved,
            keyboard: saved,
            icon: L.divIcon({
              className: 'passport-map-marker', html: pinContent(symbol, saved),
              iconSize: [38, 38], iconAnchor: [19, 19],
            }),
          }).addTo(layer);
          if (onClick) {
            const element = marker.getElement();
            element.setAttribute('aria-label', label);
            element.addEventListener('keydown', event => {
              if (event.key !== 'Enter' && event.key !== ' ') return;
              event.preventDefault();
              event.stopPropagation();
              onClick();
            });
            marker.on('click', onClick);
          }
        }
      },
      setView(location, level) { map.setView(location, level); },
      getCenter() {
        const {lat, lng} = map.getCenter().wrap();
        return {lat, lng};
      },
      fitLocations(locations) {
        if (locations.length) {
          map.fitBounds(locations, {padding: [44, 44], maxZoom: locations.length === 1 ? 15 : 16, animate: false});
        }
      },
      resize() { map.invalidateSize({pan: false}); },
    };
  }

  function loadGoogle(key) {
    googleRequest ??= (async () => {
      const previousFailure = window.gm_authFailure;
      googleAuthFailed = new Promise(resolve => {
        window.gm_authFailure = () => {
          resolve(false);
          previousFailure?.();
        };
      });
      const url = new URL('https://maps.googleapis.com/maps/api/js');
      url.search = new URLSearchParams({key, v: 'weekly'});
      await loadAsset('script', {src: url.href});
      const maps = window.google.maps;
      let timer;
      try {
        return await Promise.race([
          Promise.all([maps.importLibrary('maps'), maps.importLibrary('marker'), maps.importLibrary('core')]),
          new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error('Google Maps libraries timed out')), loadTimeout);
          }),
        ]);
      } finally {
        clearTimeout(timer);
      }
    })();
    return googleRequest;
  }

  async function createGoogle(container, {center, zoom, onPick}, {googleMapsKey, googleMapsMapId}) {
    const [{Map}, {AdvancedMarkerElement}, {ControlPosition, LatLngBounds}] = await loadGoogle(googleMapsKey);
    const surface = document.createElement('div');
    surface.className = 'passport-map-google';
    surface.style.height = '100%';
    container.append(surface);
    const map = new Map(surface, {
      center, zoom, mapId: googleMapsMapId || 'DEMO_MAP_ID', gestureHandling: 'cooperative',
      clickableIcons: false, streetViewControl: false, mapTypeControl: false, fullscreenControl: false,
      cameraControl: false, zoomControl: true,
      zoomControlOptions: {position: ControlPosition.INLINE_END_BLOCK_END},
    });
    let timer;
    let tileListener;
    const tilesLoaded = new Promise(resolve => {
      timer = setTimeout(() => resolve(false), loadTimeout);
      tileListener = map.addListener('tilesloaded', () => resolve(true));
    });
    const ready = await Promise.race([tilesLoaded, googleAuthFailed]);
    clearTimeout(timer);
    tileListener.remove();
    if (!ready) throw new Error('Google Maps did not render');

    if (onPick) map.addListener('click', event => {
      if (event.latLng) onPick(event.latLng.toJSON());
    });
    let active = [];
    return {
      setMarkers(markers) {
        for (const marker of active) marker.map = null;
        active = markers.map(({lat, lng, symbol, label, onClick}) => {
          const marker = new AdvancedMarkerElement({
            map, position: {lat, lng}, title: label, gmpClickable: Boolean(onClick), anchorTop: '-50%',
          });
          marker.append(pinContent(symbol, Boolean(onClick)));
          if (onClick) marker.addEventListener('gmp-click', onClick);
          return marker;
        });
      },
      setView(location, level) { map.moveCamera({center: location, zoom: level}); },
      getCenter() { return map.getCenter()?.toJSON(); },
      fitLocations(locations) {
        if (!locations.length) return;
        if (locations.every(({lat, lng}) => lat === locations[0].lat && lng === locations[0].lng)) {
          map.moveCamera({center: locations[0], zoom: 15});
          return;
        }
        const bounds = new LatLngBounds();
        for (const location of locations) bounds.extend(location);
        map.fitBounds(bounds, 44);
      },
      resize() {},
    };
  }

  window.ChoobPassportMap = {
    async create(container, options) {
      container.classList.add(options.onPick ? 'passport-map-picker' : 'passport-map-collection');
      const config = await mapConfig();
      if (config?.googleMapsKey) {
        try {
          return await createGoogle(container, options, config);
        } catch {
          container.replaceChildren();
          options.onStatus?.('Google Maps could not load. Showing OpenStreetMap.');
        }
      }
      try {
        return await createLeaflet(container, options);
      } catch (error) {
        options.onStatus?.('Map unavailable. Check your connection and reopen the map.');
        throw error;
      }
    },
  };
})();
