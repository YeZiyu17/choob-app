(() => {
  const dishTypes = [
    ['sushi', 'Sushi', '🍣', /\b(sushi|nigiri|maki|(?:tuna|salmon|california|avocado) rolls?)\b|寿司|壽司/],
    ['sashimi', 'Sashimi', '🐟', /\bsashimi\b|刺身/],
    ['ramen', 'Ramen', '🍜', /\bramen\b|拉面|拉麵|ラーメン/],
    ['pho', 'Pho', '🍜', /\bpho\b|越南粉/],
    ['pad-thai', 'Pad Thai', '🍜', /\bpad thai\b|泰式炒河粉/],
    ['dumplings', 'Dumplings', '🥟', /\b(dumplings?|gyoza|pot ?stickers?|jiaozi)\b|饺子|餃子/],
    ['fried-rice', 'Fried rice', '🍚', /\bfried rice\b|炒饭|炒飯/],
    ['pizza', 'Pizza', '🍕', /\bpizzas?\b|披萨|披薩/],
    ['burgers', 'Burgers', '🍔', /\b(burgers?|hamburgers?|cheeseburgers?)\b|汉堡|漢堡/],
    ['tacos', 'Tacos', '🌮', /\btacos?\b/],
    ['pasta', 'Pasta', '🍝', /\b(pasta|spaghetti|fettuccine|linguine|penne)\b|意大利面|意大利麵/],
    ['hot-pot', 'Hot pot', '🥘', /\bhot ?pot\b|火锅|火鍋/],
  ];

  const sampleProfiles = [
    {id: 'amelia', name: 'Amelia', emoji: '🍣', description: 'Sample passport · Sushi and dumplings',
      dishes: ['Salmon nigiri', 'Pork gyoza', 'Shrimp pad thai']},
    {id: 'maya', name: 'Maya', emoji: '🍜', description: 'Sample passport · Ramen and sushi',
      dishes: ['Spicy tuna roll', 'Tonkotsu ramen', 'Mushroom pasta']},
    {id: 'leo', name: 'Leo', emoji: '🌮', description: 'Sample passport · Pizza and tacos',
      dishes: ['Margherita pizza', 'Baja fish tacos', 'Cheeseburger']},
  ];

  function stampType(name) {
    if (typeof name !== 'string') return null;
    const label = name.normalize('NFKC').trim().replace(/\s+/gu, ' ');
    if (!label || label.length > 120 || /[<>\p{Cc}\p{Cf}]/u.test(label)) return null;
    const words = label.toLowerCase().normalize('NFD')
      .replace(/(\p{Script=Latin})\p{M}+/gu, '$1')
      .replace(/[^\p{L}\p{M}\p{N}]+/gu, ' ').trim();
    if (!/[\p{L}\p{N}]/u.test(words) || /^(unknown|uncertain|unsupported(?: dish)?|uncertain unsupported dish)$/.test(words)) return null;

    const families = dishTypes.filter(([, , , aliases]) => aliases.test(words));
    if (families.length === 1) {
      const [key, canonicalLabel, emoji] = families[0];
      return {key, label: canonicalLabel, emoji};
    }
    return {key: words.replace(/ /g, '-'), label, emoji: '🍽️'};
  }

  function matchStamps(meals) {
    const stampTypes = new Map();
    for (const meal of Array.isArray(meals) ? meals : []) {
      const location = meal?.location;
      if (!location || !Number.isFinite(location.lat) || Math.abs(location.lat) > 90 ||
          !Number.isFinite(location.lng) || Math.abs(location.lng) > 180) continue;
      const type = stampType(meal.dish_name);
      if (type && !stampTypes.has(type.key)) stampTypes.set(type.key, type);
    }

    const matches = sampleProfiles.map(({dishes: names, ...profile}) => {
      const types = names.map(stampType);
      const dishes = names.map((name, index) => ({name, key: types[index].key, emoji: types[index].emoji}));
      const shared = [...new Set(dishes.map(dish => dish.key))]
        .filter(key => stampTypes.has(key)).map(key => ({...stampTypes.get(key)}));
      const suggestions = dishes.filter(dish => !stampTypes.has(dish.key));
      return {...profile, shared, dishes, suggestions};
    }).filter(match => match.shared.length > 0);
    matches.sort((a, b) => b.shared.length - a.shared.length || a.id.localeCompare(b.id, 'en'));

    return {stampTypes: [...stampTypes.values()], matches};
  }

  window.ChoobConnect = Object.freeze({matchStamps});
})();
