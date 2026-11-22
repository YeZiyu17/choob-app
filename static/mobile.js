/* Progressive enhancement only: keep the original app and storage contracts. */
(() => {
  'use strict';
  const installed = () => matchMedia('(display-mode: standalone)').matches
    || matchMedia('(display-mode: fullscreen)').matches || navigator.standalone === true;
  const appleMobile = /iPhone|iPad|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const android = /Android/.test(navigator.userAgent);
  const homeTop = document.querySelector('#discover .top');
  let installPrompt = null;
  let dialog = null;
  let button = null;

  function showInstallHelp() {
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.className = 'mobile-install-dialog';
      dialog.setAttribute('aria-labelledby', 'mobileInstallTitle');
      const steps = appleMobile
        ? ['Open Choob in Safari.', 'Tap Share, then Add to Home Screen.', 'If shown, turn on Open as Web App, then tap Add.']
        : android
          ? ['Open Choob in Chrome.', 'Open the browser menu (⋮).', 'Choose Install app or Add to Home screen.']
          : ['Open Choob in Chrome or Edge.', 'Choose the install option in the address bar or browser menu.', 'Open Choob from its new app icon.'];
      dialog.innerHTML = '<img src="/static/icons/apple-touch-icon.png" alt="">'
        + '<h2 id="mobileInstallTitle">A home for your food story.</h2>'
        + '<p>Add Choob to your home screen for a little less browser and a little more bite.</p>'
        + '<ol>' + steps.map(step => '<li>' + step + '</li>').join('') + '</ol>'
        + '<p>' + (window.isSecureContext
          ? 'Photo recognition and recommendations still need a connection to Choob.'
          : 'For the full app experience, open the secure Choob link. This link may only support a shortcut.') + '</p>'
        + '<button type="button">Got it</button>';
      dialog.querySelector('button').addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', event => {
        const rect = dialog.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right
            || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
      });
      document.body.append(dialog);
    }
    dialog.showModal();
  }

  if (homeTop && !installed()) {
    button = document.createElement('button');
    button.type = 'button';
    button.className = 'mobile-install-button';
    button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M5 15v5h14v-5"/></svg><span>Install Choob</span>';
    button.addEventListener('click', async () => {
      if (!installPrompt) return showInstallHelp();
      const prompt = installPrompt;
      installPrompt = null;
      try {
        await prompt.prompt();
        const choice = await prompt.userChoice;
        if (choice.outcome === 'accepted') button.hidden = true;
      } catch {
        showInstallHelp();
      }
    });
    homeTop.append(button);
  }
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = null;
    if (button) button.hidden = true;
    if (dialog?.open) dialog.close();
  });

  // Some mobile browsers resize only visualViewport when the keyboard opens.
  // Updating the app height keeps form controls above the keyboard without
  // modifying the business UI or preventing the user from pinch-zooming.
  if (window.visualViewport) {
    let frame = 0;
    function fitVisibleViewport() {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (window.visualViewport.scale !== 1) return;
        document.documentElement.style.setProperty('--mobile-viewport-height', window.visualViewport.height + 'px');
      });
    }
    window.visualViewport.addEventListener('resize', fitVisibleViewport);
    window.addEventListener('orientationchange', fitVisibleViewport);
    window.addEventListener('pageshow', fitVisibleViewport);
    fitVisibleViewport();
  }

  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/service-worker.js', {scope: '/', updateViaCache: 'none'})
      .catch(error => console.warn('Choob offline help is unavailable:', error));
  }
})();
