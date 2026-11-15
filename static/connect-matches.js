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

  // Demo passports. Restaurants are invented for the demo.
  const sampleProfiles = [
    {id: 'amelia', name: 'Amelia', emoji: '🍣', city: 'Philadelphia', bio: 'Weekend sushi counter regular. Always orders the dumplings.',
      dishes: [
        {name: 'Salmon nigiri', restaurant: 'Kaze Sushi Bar', city: 'Philadelphia', note: 'Buttery salmon, rice still warm.'},
        {name: 'Pork gyoza', restaurant: 'Kaze Sushi Bar', city: 'Philadelphia', note: 'Crispy bottoms. Get two orders.'},
        {name: 'Soup dumplings', restaurant: 'Golden Steam', city: 'Philadelphia', note: 'Bite a corner first, the broth is hot.'},
        {name: 'Shrimp pad thai', restaurant: 'Lemongrass Corner', city: 'Philadelphia', note: 'Ask for extra lime.'},
      ]},
    {id: 'maya', name: 'Maya', emoji: '🍜', city: 'New York', bio: 'On a mission to rank every bowl of noodles in Manhattan.',
      dishes: [
        {name: 'Tonkotsu ramen', restaurant: 'Ichiban Alley', city: 'New York', note: 'Rich broth, perfect soft egg.'},
        {name: 'Spicy tuna roll', restaurant: 'Fin & Rice', city: 'New York', note: 'Good heat, generous tuna.'},
        {name: 'Beef pho', restaurant: 'Saigon Steam', city: 'New York', note: 'Clear broth that tastes like hours of work.'},
        {name: 'Mushroom pasta', restaurant: 'Nonna Lu', city: 'New York', note: 'Earthy, creamy, worth the wait.'},
      ]},
    {id: 'leo', name: 'Leo', emoji: '🌮', city: 'Philadelphia', bio: 'Comfort food first. Will cross town for a good taco.',
      dishes: [
        {name: 'Margherita pizza', restaurant: 'Forno Nove', city: 'Philadelphia', note: 'Charred crust, bright sauce.'},
        {name: 'Baja fish tacos', restaurant: 'La Brisa Taqueria', city: 'Philadelphia', note: 'Crunchy batter, tangy slaw.'},
        {name: 'Philly cheesesteak', restaurant: 'Broad St. Grill', city: 'Philadelphia', note: 'Wit onions. Trust me.'},
        {name: 'Cheeseburger', restaurant: 'Patty Lab', city: 'Philadelphia', note: 'Smash style with crispy edges.'},
      ]},
    {id: 'priya', name: 'Priya', emoji: '🍛', city: 'Chicago', bio: 'Spice seeker. Curry on Sundays, dumplings any day.',
      dishes: [
        {name: 'Butter chicken', restaurant: 'Saffron House', city: 'Chicago', note: 'Silky sauce. Order garlic naan.'},
        {name: 'Lamb biryani', restaurant: 'Saffron House', city: 'Chicago', note: 'Fragrant rice, tender lamb.'},
        {name: 'Green curry', restaurant: 'Basil Thai Kitchen', city: 'Chicago', note: 'Coconut-y with a slow burn.'},
        {name: 'Mapo tofu', restaurant: 'Red Pepper Sichuan', city: 'Chicago', note: 'Numbing in the best way.'},
      ]},
    {id: 'jun', name: 'Jun', emoji: '🥩', city: 'Los Angeles', bio: 'Koreatown local. Knows every late-night spot.',
      dishes: [
        {name: 'Galbi', restaurant: 'Seoul Fire BBQ', city: 'Los Angeles', note: 'Sweet marinade, grilled at the table.'},
        {name: 'Dolsot bibimbap', restaurant: 'Hanok Table', city: 'Los Angeles', note: 'Let the rice crisp in the stone bowl.'},
        {name: 'Tteokbokki', restaurant: 'Hanok Table', city: 'Los Angeles', note: 'Chewy and spicy-sweet.'},
        {name: 'Pork dumplings', restaurant: 'Mandu Bros', city: 'Los Angeles', note: 'Juicy filling, thin wrappers.'},
      ]},
    {id: 'sofia', name: 'Sofia', emoji: '🍝', city: 'San Francisco', bio: 'Fresh pasta fan who still makes room for tacos.',
      dishes: [
        {name: 'Cacio e pepe spaghetti', restaurant: 'Trattoria Rosa', city: 'San Francisco', note: 'Peppery and simple.'},
        {name: 'Mushroom risotto', restaurant: 'Trattoria Rosa', city: 'San Francisco', note: 'Creamy and earthy.'},
        {name: 'Carnitas burrito', restaurant: 'Mission Rojo', city: 'San Francisco', note: 'Huge. Split it or skip lunch.'},
        {name: 'Wood-fired pizza', restaurant: 'Ember Pie', city: 'San Francisco', note: 'Leopard-spotted crust.'},
      ]},
    {id: 'omar', name: 'Omar', emoji: '🧆', city: 'New York', bio: 'Street food explorer, from falafel carts to fried chicken.',
      dishes: [
        {name: 'Falafel wrap', restaurant: 'Cedar Cart', city: 'New York', note: 'Green inside, crunchy outside.'},
        {name: 'Chicken shawarma', restaurant: 'Cedar Cart', city: 'New York', note: 'Extra garlic sauce.'},
        {name: 'Nashville hot fried chicken', restaurant: 'Hot Coop', city: 'New York', note: 'Start at medium heat.'},
        {name: 'Chicken fried rice', restaurant: 'Wok Star', city: 'New York', note: 'Smoky wok flavor.'},
      ]},
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

  function hasLocation(meal) {
    const location = meal?.location;
    return Boolean(location && Number.isFinite(location.lat) && Math.abs(location.lat) <= 90 &&
      Number.isFinite(location.lng) && Math.abs(location.lng) <= 180);
  }

  // Each logged meal can hold several dishes. Every dish counts as a taste.
  function userTastes(meals) {
    const stampTypes = new Map();
    const cuisines = new Map();
    const places = [];
    for (const meal of Array.isArray(meals) ? meals : []) {
      if (!meal || typeof meal !== 'object') continue;
      const located = hasLocation(meal);
      if (located && typeof meal.location.label === 'string' && meal.location.label.trim()) {
        places.push(meal.location.label.trim().toLowerCase());
      }
      const dishes = Array.isArray(meal.dishes) && meal.dishes.length ? meal.dishes : [meal];
      for (const dish of dishes) {
        const type = stampType(dish?.dish_name, dish?.cuisine ?? meal.cuisine);
        if (!type) continue;
        const existing = stampTypes.get(type.key);
        if (existing) {
          existing.count += 1;
          existing.located ||= located;
        } else {
          stampTypes.set(type.key, {...type, count: 1, located});
        }
        if (type.cuisine) cuisines.set(type.cuisine.toLowerCase(), type.cuisine);
      }
    }
    return {stampTypes, cuisines, places};
  }

  function listPhrase(items) {
    if (items.length <= 1) return items.join('');
    return `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`;
  }

  function buildReason(profile, shared, sharedCuisines, sameCity) {
    const parts = [];
    if (shared.length) {
      parts.push(`You both have ${listPhrase(shared.slice(0, 3).map(type => type.label))} in your passports`);
    }
    if (sharedCuisines.length) {
      parts.push(`${shared.length ? 'and' : 'You'} both like ${listPhrase(sharedCuisines.slice(0, 2))} food`);
    }
    let reason = parts.join(' ');
    if (sameCity) reason += `${reason ? ', and' : 'You'} both eat around ${profile.city}`;
    return reason ? `${reason}.` : `${profile.name} eats around ${profile.city}.`;
  }

  // Scoring: a shared dish type is worth 3, a shared cuisine without a shared dish 1,
  // and a meal logged at a place whose name mentions the profile's city 1.
  function scoreProfile(profile, tastes) {
    const dishes = profile.dishes.map(dish => {
      const type = stampType(dish.name);
      return {...dish, key: type.key, emoji: type.emoji, typeLabel: type.label, cuisine: type.cuisine};
    });
    const profileKeys = [...new Set(dishes.map(dish => dish.key))];
    const shared = profileKeys.filter(key => tastes.stampTypes.has(key))
      .map(key => {
        const mine = tastes.stampTypes.get(key);
        return {key, label: mine.label, emoji: mine.emoji, cuisine: mine.cuisine};
      });
    const sharedCuisineKeys = new Set(shared.map(type => type.cuisine?.toLowerCase()).filter(Boolean));
    const sharedCuisines = [...new Set(dishes.map(dish => dish.cuisine).filter(Boolean))]
      .filter(cuisine => tastes.cuisines.has(cuisine.toLowerCase()) && !sharedCuisineKeys.has(cuisine.toLowerCase()));
    const cityName = profile.city.toLowerCase();
    const sameCity = tastes.places.some(place => place.includes(cityName));

    const score = shared.length * 3 + sharedCuisines.length + (sameCity ? 1 : 0);
    const strength = shared.length >= 2 || score >= 5 ? 'Strong match' : score >= 3 ? 'Good match' : score > 0 ? 'Some overlap' : '';
    const suggestions = dishes.filter(dish => !tastes.stampTypes.has(dish.key))
      .map(dish => ({...dish, sharedCuisine: Boolean(dish.cuisine && tastes.cuisines.has(dish.cuisine.toLowerCase()))}))
      // Dishes from a cuisine you already like come first.
      .sort((a, b) => Number(b.sharedCuisine) - Number(a.sharedCuisine));
    const sharedDishes = dishes.filter(dish => tastes.stampTypes.has(dish.key));
    const {dishes: _unused, ...rest} = profile;
    return {
      ...rest,
      score, strength, shared, sharedCuisines, sameCity,
      reason: buildReason(profile, shared, sharedCuisines, sameCity),
      dishes, sharedDishes, suggestions,
    };
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
      matches, explore,
    };
  }

  window.ChoobConnect = Object.freeze({matchStamps, stampType});
})();
