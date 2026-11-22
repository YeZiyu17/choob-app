(() => {
  // Dish families: [key, label, emoji, cuisine, aliases]. Aliases run on lowercased,
  // accent-free names with punctuation turned into spaces. The first family that matches wins.
  const dishTypes = [
    ['sashimi', 'Sashimi', '🐟', 'Japanese', /\bsashimi\b|刺身/],
    ['sushi', 'Sushi', '🍣', 'Japanese', /\b(sushi|nigiri|maki|(?:tuna|salmon|california|avocado|dragon|rainbow|eel) rolls?)\b|寿司|壽司/],
    ['ramen', 'Ramen', '🍜', 'Japanese', /\bramen\b|拉面|拉麵|ラーメン/],
    ['udon', 'Udon', '🍜', 'Japanese', /\budon\b|乌冬|烏龍麵/],
    ['tempura', 'Tempura', '🍤', 'Japanese', /\btempura\b|天妇罗|天婦羅/],
    ['pho', 'Pho', '🍲', 'Vietnamese', /\bpho\b|越南粉|河粉汤/],
    ['banh-mi', 'Banh mi', '🥖', 'Vietnamese', /\bbanh mi\b/],
    ['pad-thai', 'Pad Thai', '🍝', 'Thai', /\bpad thai\b|泰式炒河粉/],
    ['thai-curry', 'Thai curry', '🍛', 'Thai', /\b(green|red|yellow|panang|massaman) curry\b|泰式咖喱/],
    ['indian-curry', 'Indian curry', '🍛', 'Indian', /\b(tikka masala|butter chicken|korma|vindaloo|saag|palak paneer|dal makhani)\b/],
    ['biryani', 'Biryani', '🍚', 'Indian', /\bbiryani\b/],
    ['dumplings', 'Dumplings', '🥟', 'Chinese', /\b(dumplings?|gyoza|pot ?stickers?|jiaozi|xiao ?long ?bao|soup dumplings?|wontons?|har gow|shumai|siu mai)\b|饺子|餃子|小笼包|小籠包|馄饨|餛飩/],
    ['fried-rice', 'Fried rice', '🍚', 'Chinese', /\bfried rice\b|炒饭|炒飯/],
    ['mapo-tofu', 'Mapo tofu', '🌶️', 'Chinese', /\bma ?po tofu\b|麻婆豆腐/],
    ['peking-duck', 'Peking duck', '🦆', 'Chinese', /\b(peking|roast) duck\b|北京烤鸭|烤鴨/],
    ['hot-pot', 'Hot pot', '🫕', 'Chinese', /\bhot ?pot\b|火锅|火鍋/],
    ['bibimbap', 'Bibimbap', '🍲', 'Korean', /\bbibimbap\b|拌饭|拌飯/],
    ['korean-bbq', 'Korean BBQ', '🥩', 'Korean', /\b(korean bbq|korean barbecue|bulgogi|galbi|kalbi|samgyeopsal)\b|韩式烤肉/],
    ['tteokbokki', 'Tteokbokki', '🍢', 'Korean', /\btteokbokki\b|炒年糕/],
    ['pizza', 'Pizza', '🍕', 'Italian', /\bpizzas?\b|披萨|披薩/],
    ['pasta', 'Pasta', '🍝', 'Italian', /\b(pasta|spaghetti|fettuccine|linguine|penne|rigatoni|lasagna|carbonara|gnocchi)\b|意大利面|意大利麵/],
    ['risotto', 'Risotto', '🍚', 'Italian', /\brisotto\b/],
    ['cheesesteak', 'Cheesesteak', '🥪', 'American', /\bcheese ?steaks?\b/],
    ['burgers', 'Burgers', '🍔', 'American', /\b(burgers?|hamburgers?|cheeseburgers?)\b|汉堡|漢堡/],
    ['fried-chicken', 'Fried chicken', '🍗', 'American', /\bfried chicken\b|炸鸡|炸雞/],
    ['bbq', 'BBQ', '🍖', 'American', /\b(brisket|bbq ribs|pulled pork|smoked ribs|barbecue ribs)\b/],
    ['tacos', 'Tacos', '🌮', 'Mexican', /\btacos?\b|塔可/],
    ['burrito', 'Burritos', '🌯', 'Mexican', /\bburritos?\b/],
    ['enchiladas', 'Enchiladas', '🫔', 'Mexican', /\benchiladas?\b/],
    ['falafel', 'Falafel', '🧆', 'Middle Eastern', /\bfalafel\b/],
    ['shawarma', 'Shawarma', '🥙', 'Middle Eastern', /\b(shawarma|gyros?|doner)\b/],
  ];

  function stampType(name, fallbackCuisine = null) {
    if (typeof name !== 'string') return null;
    const label = name.normalize('NFKC').trim().replace(/\s+/gu, ' ');
    if (!label || label.length > 120 || /[<>\p{Cc}\p{Cf}]/u.test(label)) return null;
    const words = label.toLowerCase().normalize('NFD')
      .replace(/(\p{Script=Latin})\p{M}+/gu, '$1')
      .replace(/[^\p{L}\p{M}\p{N}]+/gu, ' ').trim();
    if (!/[\p{L}\p{N}]/u.test(words) || /^(unknown|uncertain|unsupported(?: dish)?|uncertain unsupported dish)$/.test(words)) return null;

    const family = dishTypes.find(([, , , , aliases]) => aliases.test(words));
    if (family) {
      const [key, canonicalLabel, emoji, cuisine] = family;
      return {key, label: canonicalLabel, emoji, cuisine};
    }
    const cuisine = typeof fallbackCuisine === 'string' && fallbackCuisine.trim() &&
      !/^unknown$/i.test(fallbackCuisine.trim()) ? fallbackCuisine.trim() : null;
    return {key: words.replace(/ /g, '-'), label, emoji: '🍽️', cuisine};
  }

  // Demo passports. Restaurants are invented for the demo; addresses are neighborhoods only.
  const place = (address, lat, lng) => ({address, lat, lng});
  const P = {
    phlChinatown: place('Chinatown, Philadelphia, PA', 39.9555, -75.1547),
    phlChinatown2: place('Race St, Chinatown, Philadelphia, PA', 39.9548, -75.1560),
    phlRittenhouse: place('Rittenhouse, Philadelphia, PA', 39.9496, -75.1718),
    phlPassyunk: place('East Passyunk, Philadelphia, PA', 39.9289, -75.1645),
    phlFishtown: place('Fishtown, Philadelphia, PA', 39.9727, -75.1340),
    phlCenter: place('Center City, Philadelphia, PA', 39.9526, -75.1635),
    nycEastVillage: place('East Village, New York, NY', 40.7265, -73.9815),
    nycMidtown: place('Midtown, New York, NY', 40.7549, -73.9840),
    nycFlushing: place('Flushing, Queens, New York, NY', 40.7580, -73.8303),
    nycWestVillage: place('West Village, New York, NY', 40.7336, -74.0027),
    nycAstoria: place('Astoria, Queens, New York, NY', 40.7644, -73.9235),
    nycLES: place('Lower East Side, New York, NY', 40.7150, -73.9843),
    chiDevon: place('Devon Ave, Chicago, IL', 41.9978, -87.6897),
    chiUptown: place('Uptown, Chicago, IL', 41.9665, -87.6533),
    chiChinatown: place('Chinatown, Chicago, IL', 41.8523, -87.6324),
    laKtown: place('Koreatown, Los Angeles, CA', 34.0618, -118.3004),
    laKtown2: place('Wilshire Blvd, Koreatown, Los Angeles, CA', 34.0625, -118.3090),
    laSawtelle: place('Sawtelle, Los Angeles, CA', 34.0383, -118.4430),
    sfNorthBeach: place('North Beach, San Francisco, CA', 37.8061, -122.4103),
    sfMission: place('Mission District, San Francisco, CA', 37.7599, -122.4148),
    sfRichmond: place('Inner Richmond, San Francisco, CA', 37.7802, -122.4645),
  };
  const dish = (name, restaurant, city, where, rating, note) => ({name, restaurant, city, ...where, rating, note});
  const sampleProfiles = [
    {id: 'amelia', name: 'Amelia', emoji: '🍣', city: 'Philadelphia', bio: 'Weekend sushi counter regular. Always orders the dumplings.',
      dishes: [
        dish('Salmon nigiri', 'Kaze Sushi Bar', 'Philadelphia', P.phlRittenhouse, 5, 'Buttery salmon, rice still warm.'),
        dish('Pork gyoza', 'Kaze Sushi Bar', 'Philadelphia', P.phlRittenhouse, 4, 'Crispy bottoms. Get two orders.'),
        dish('Soup dumplings', 'Golden Steam', 'Philadelphia', P.phlChinatown, 5, 'Bite a corner first, the broth is hot.'),
        dish('Shrimp pad thai', 'Lemongrass Corner', 'Philadelphia', P.phlCenter, 4, 'Ask for extra lime.'),
      ]},
    {id: 'maya', name: 'Maya', emoji: '🍜', city: 'New York', bio: 'On a mission to rank every bowl of noodles in Manhattan.',
      dishes: [
        dish('Tonkotsu ramen', 'Ichiban Alley', 'New York', P.nycEastVillage, 5, 'Rich broth, perfect soft egg.'),
        dish('Spicy tuna roll', 'Fin & Rice', 'New York', P.nycMidtown, 4, 'Good heat, generous tuna.'),
        dish('Beef pho', 'Saigon Steam', 'New York', P.nycLES, 4, 'Clear broth that tastes like hours of work.'),
        dish('Mushroom pasta', 'Nonna Lu', 'New York', P.nycWestVillage, 3, 'Earthy and creamy, a bit heavy.'),
      ]},
    {id: 'leo', name: 'Leo', emoji: '🌮', city: 'Philadelphia', bio: 'Comfort food first. Will cross town for a good taco.',
      dishes: [
        dish('Margherita pizza', 'Forno Nove', 'Philadelphia', P.phlFishtown, 5, 'Charred crust, bright sauce.'),
        dish('Baja fish tacos', 'La Brisa Taqueria', 'Philadelphia', P.phlPassyunk, 4, 'Crunchy batter, tangy slaw.'),
        dish('Philly cheesesteak', 'Broad St. Grill', 'Philadelphia', P.phlCenter, 5, 'Wit onions. Trust me.'),
        dish('Cheeseburger', 'Patty Lab', 'Philadelphia', P.phlFishtown, 4, 'Smash style with crispy edges.'),
      ]},
    {id: 'priya', name: 'Priya', emoji: '🍛', city: 'Chicago', bio: 'Spice seeker. Curry on Sundays, dumplings any day.',
      dishes: [
        dish('Butter chicken', 'Saffron House', 'Chicago', P.chiDevon, 5, 'Silky sauce. Order garlic naan.'),
        dish('Lamb biryani', 'Saffron House', 'Chicago', P.chiDevon, 4, 'Fragrant rice, tender lamb.'),
        dish('Green curry', 'Basil Thai Kitchen', 'Chicago', P.chiUptown, 4, 'Coconut-y with a slow burn.'),
        dish('Mapo tofu', 'Red Pepper Sichuan', 'Chicago', P.chiChinatown, 5, 'Numbing in the best way.'),
      ]},
    {id: 'jun', name: 'Jun', emoji: '🥩', city: 'Los Angeles', bio: 'Koreatown local. Knows every late-night spot.',
      dishes: [
        dish('Galbi', 'Seoul Fire BBQ', 'Los Angeles', P.laKtown, 5, 'Sweet marinade, grilled at the table.'),
        dish('Dolsot bibimbap', 'Hanok Table', 'Los Angeles', P.laKtown2, 4, 'Let the rice crisp in the stone bowl.'),
        dish('Tteokbokki', 'Hanok Table', 'Los Angeles', P.laKtown2, 4, 'Chewy and spicy-sweet.'),
        dish('Pork dumplings', 'Mandu Bros', 'Los Angeles', P.laSawtelle, 3, 'Juicy, but the wrappers were thick.'),
      ]},
    {id: 'sofia', name: 'Sofia', emoji: '🍝', city: 'San Francisco', bio: 'Fresh pasta fan who still makes room for tacos.',
      dishes: [
        dish('Cacio e pepe spaghetti', 'Trattoria Rosa', 'San Francisco', P.sfNorthBeach, 5, 'Peppery and simple.'),
        dish('Mushroom risotto', 'Trattoria Rosa', 'San Francisco', P.sfNorthBeach, 4, 'Creamy and earthy.'),
        dish('Carnitas burrito', 'Mission Rojo', 'San Francisco', P.sfMission, 4, 'Huge. Split it or skip lunch.'),
        dish('Wood-fired pizza', 'Ember Pie', 'San Francisco', P.sfRichmond, 5, 'Leopard-spotted crust.'),
      ]},
    {id: 'omar', name: 'Omar', emoji: '🧆', city: 'New York', bio: 'Street food explorer, from falafel carts to fried chicken.',
      dishes: [
        dish('Falafel wrap', 'Cedar Cart', 'New York', P.nycAstoria, 5, 'Green inside, crunchy outside.'),
        dish('Chicken shawarma', 'Cedar Cart', 'New York', P.nycAstoria, 4, 'Extra garlic sauce.'),
        dish('Nashville hot fried chicken', 'Hot Coop', 'New York', P.nycLES, 4, 'Start at medium heat.'),
        dish('Chicken fried rice', 'Wok Star', 'New York', P.nycFlushing, 3, 'Smoky, but a little salty.'),
      ]},
  ];

  // Ratings: 4–5 means you loved it, 1–2 means you didn't like it. Unrated dishes still count.
  const LOVED = 4;
  const DISLIKED = 2;

  function validRating(value) {
    return Number.isInteger(value) && value >= 1 && value <= 5 ? value : null;
  }

  function placeKey(name) {
    return typeof name === 'string'
      ? name.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()
      : '';
  }

  function hasLocation(meal) {
    const location = meal?.location;
    return Boolean(location && Number.isFinite(location.lat) && Math.abs(location.lat) <= 90 &&
      Number.isFinite(location.lng) && Math.abs(location.lng) <= 180);
  }

  // Each logged meal can hold several dishes. Every dish counts as a taste unless you rated it low.
  function userTastes(meals) {
    const stampTypes = new Map();
    const cuisines = new Map();
    const disliked = new Map();
    const restaurants = new Map();
    const places = [];
    for (const meal of Array.isArray(meals) ? meals : []) {
      if (!meal || typeof meal !== 'object') continue;
      const located = hasLocation(meal);
      for (const text of [meal.address, meal.restaurant_name, located ? meal.location.label : null]) {
        if (typeof text === 'string' && text.trim()) places.push(text.trim().toLowerCase());
      }
      const restaurant = placeKey(meal.restaurant_name);
      if (restaurant) restaurants.set(restaurant, meal.restaurant_name.trim());
      const dishes = Array.isArray(meal.dishes) && meal.dishes.length ? meal.dishes : [meal];
      for (const item of dishes) {
        const type = stampType(item?.dish_name, item?.cuisine ?? meal.cuisine);
        if (!type) continue;
        const rating = validRating(item?.rating);
        if (rating !== null && rating <= DISLIKED) {
          disliked.set(type.key, {...type, rating});
          continue;
        }
        const existing = stampTypes.get(type.key);
        if (existing) {
          existing.count += 1;
          existing.located ||= located;
          if (rating !== null && (existing.rating === null || rating > existing.rating)) existing.rating = rating;
        } else {
          stampTypes.set(type.key, {...type, count: 1, located, rating});
        }
        if (type.cuisine) cuisines.set(type.cuisine.toLowerCase(), type.cuisine);
      }
    }
    // A dish type you rated well elsewhere is a taste, not a dislike.
    for (const key of stampTypes.keys()) disliked.delete(key);
    return {stampTypes, cuisines, disliked, restaurants, places};
  }

  function listPhrase(items) {
    if (items.length <= 1) return items.join('');
    return `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`;
  }

  function stars(rating) {
    return `${rating}★`;
  }

  function buildReason(profile, match) {
    const parts = [];
    if (match.sharedRestaurants.length) {
      parts.push(`you’ve both been to ${listPhrase(match.sharedRestaurants.slice(0, 2))}`);
    }
    for (const type of match.lovedShared.slice(0, 2)) {
      parts.push(type.mine === type.theirs
        ? `you both rated ${type.label} ${stars(type.mine)}`
        : `you rated ${type.label} ${stars(type.mine)} and ${profile.name} gave it ${stars(type.theirs)}`);
    }
    const otherShared = match.shared.filter(type => !match.lovedShared.some(loved => loved.key === type.key));
    if (otherShared.length && parts.length < 3) {
      parts.push(`you both have ${listPhrase(otherShared.slice(0, 3).map(type => type.label))} in your passports`);
    }
    if (match.sharedCuisines.length && parts.length < 3) {
      parts.push(`you both like ${listPhrase(match.sharedCuisines.slice(0, 2))} food`);
    }
    if (match.sameCity && parts.length < 3) parts.push(`you both eat around ${profile.city}`);
    if (!parts.length) return `${profile.name} eats around ${profile.city}.`;
    const text = listPhrase(parts);
    return `${text[0].toUpperCase()}${text.slice(1)}.`;
  }

  // Scoring: a shared dish type is worth 3, plus 1 when you both loved it (4–5★).
  // Eating at the same restaurant adds 2, a shared cuisine without a shared dish 1,
  // and a meal address or place name that mentions the profile's city 1.
  function scoreProfile(profile, tastes) {
    const dishes = profile.dishes.map(item => {
      const type = stampType(item.name);
      return {...item, key: type.key, emoji: type.emoji, typeLabel: type.label, cuisine: type.cuisine};
    });
    const profileKeys = [...new Set(dishes.map(item => item.key))];
    const shared = profileKeys.filter(key => tastes.stampTypes.has(key)).map(key => {
      const mine = tastes.stampTypes.get(key);
      const theirs = Math.max(...dishes.filter(item => item.key === key).map(item => item.rating ?? 0)) || null;
      return {key, label: mine.label, emoji: mine.emoji, cuisine: mine.cuisine, mine: mine.rating, theirs};
    });
    const lovedShared = shared.filter(type => type.mine >= LOVED && type.theirs >= LOVED)
      .sort((a, b) => (b.mine + b.theirs) - (a.mine + a.theirs));
    const sharedCuisineKeys = new Set(shared.map(type => type.cuisine?.toLowerCase()).filter(Boolean));
    const sharedCuisines = [...new Set(dishes.map(item => item.cuisine).filter(Boolean))]
      .filter(cuisine => tastes.cuisines.has(cuisine.toLowerCase()) && !sharedCuisineKeys.has(cuisine.toLowerCase()));
    const sharedRestaurants = [...new Set(dishes.map(item => item.restaurant))]
      .filter(name => tastes.restaurants.has(placeKey(name)));
    const cityName = profile.city.toLowerCase();
    const sameCity = tastes.places.some(text => text.includes(cityName));

    const score = shared.length * 3 + lovedShared.length + sharedRestaurants.length * 2 +
      sharedCuisines.length + (sameCity ? 1 : 0);
    const strength = shared.length >= 2 || score >= 6 ? 'Strong match' : score >= 3 ? 'Good match' : score > 0 ? 'Some overlap' : '';
    const suggestions = dishes.filter(item => !tastes.stampTypes.has(item.key))
      .map(item => ({
        ...item,
        sharedCuisine: Boolean(item.cuisine && tastes.cuisines.has(item.cuisine.toLowerCase())),
        youDisliked: tastes.disliked.has(item.key),
      }))
      // Cuisines you like first, then their favorites; dish types you rated low go last.
      .sort((a, b) => Number(a.youDisliked) - Number(b.youDisliked) ||
        Number(b.sharedCuisine) - Number(a.sharedCuisine) || (b.rating ?? 0) - (a.rating ?? 0));
    const sharedDishes = dishes.filter(item => tastes.stampTypes.has(item.key));
    const stamps = dishes.filter(item => Number.isFinite(item.lat) && Number.isFinite(item.lng));
    const {dishes: _unused, ...rest} = profile;
    const match = {...rest, score, strength, shared, lovedShared, sharedCuisines, sharedRestaurants, sameCity,
      dishes, sharedDishes, suggestions, stamps};
    match.reason = buildReason(profile, match);
    return match;
  }

  function matchStamps(meals) {
    const tastes = userTastes(meals);
    const scored = sampleProfiles.map(profile => scoreProfile(profile, tastes));
    scored.sort((a, b) => b.score - a.score || b.shared.length - a.shared.length || a.id.localeCompare(b.id, 'en'));
    const matches = scored.filter(profile => profile.score > 0);
    // Profiles with nothing in common yet, shown as passports to explore.
    const explore = scored.filter(profile => profile.score === 0);
    return {
      stampTypes: [...tastes.stampTypes.values()],
      cuisines: [...tastes.cuisines.values()],
      disliked: [...tastes.disliked.values()],
      matches, explore,
    };
  }

  window.ChoobConnect = Object.freeze({matchStamps, stampType});
})();
