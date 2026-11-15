"""Canonical food candidates used for provisional CLIP suggestions.

This is candidate-label coverage, not a claim that every entry is reliably
recognizable. Canonical names stay intentionally broad; aliases improve text
matching without creating duplicate review choices.
"""
from __future__ import annotations


# cuisine -> category -> [(canonical name, aliases)]
FOOD_GROUPS = {
    "Chinese": {
        "Dumplings & small plates": [
            ("dumplings", ("jiaozi", "Chinese dumplings")),
            ("soup dumplings", ("xiaolongbao", "xiao long bao")),
            ("wontons", ("wonton",)), ("potstickers", ("guotie",)),
            ("bao", ("baozi", "steamed buns")), ("dim sum", ("yum cha dishes",)),
            ("spring rolls", ("egg rolls",)), ("scallion pancakes", ("cong you bing",)),
            ("turnip cake", ("lo bak go",)), ("sesame balls", ("jian dui",)),
        ],
        "Noodles & soups": [
            ("chow mein", ("stir-fried noodles",)), ("lo mein", ("soft stir-fried noodles",)),
            ("dan dan noodles", ("dandan noodles",)), ("beef noodle soup", ("Chinese beef noodles",)),
            ("hot and sour soup", ()), ("wonton soup", ()), ("egg drop soup", ()),
            ("cold sesame noodles", ()), ("rice noodle rolls", ("cheung fun",)),
        ],
        "Rice & mains": [
            ("fried rice", ("egg fried rice", "Chinese fried rice")),
            ("congee", ("rice porridge", "zhou")), ("mapo tofu", ("ma po tofu",)),
            ("kung pao chicken", ("gong bao chicken",)), ("orange chicken", ()),
            ("sweet and sour pork", ()), ("char siu", ("Chinese barbecue pork",)),
            ("peking duck", ("Beijing roast duck",)), ("roast duck", ("Chinese roast duck",)),
            ("red braised pork", ("hong shao rou",)), ("twice-cooked pork", ("hui guo rou",)),
            ("salt and pepper shrimp", ()), ("steamed fish", ("Chinese steamed whole fish",)),
            ("hot pot", ("Chinese hotpot",)), ("mala dry pot", ("mala xiang guo",)),
            ("braised eggplant", ("Chinese eggplant",)),
            ("Chinese vegetable stir-fry", ("Chinese mixed vegetables",)),
        ],
    },
    "Japanese": {
        "Rice & noodles": [
            ("sushi", ("nigiri", "maki rolls", "Japanese sushi")), ("sashimi", ("sliced raw fish",)),
            ("ramen", ("Japanese noodle soup", "tonkotsu ramen", "shoyu ramen", "miso ramen")),
            ("udon", ("udon noodle soup",)), ("soba", ("buckwheat noodles",)),
            ("yakisoba", ("Japanese fried noodles",)), ("onigiri", ("rice balls",)),
            ("donburi", ("Japanese rice bowl",)), ("gyudon", ("beef rice bowl",)),
            ("katsudon", ("pork cutlet rice bowl",)), ("oyakodon", ("chicken and egg rice bowl",)),
            ("Japanese curry", ("curry rice", "kare raisu")), ("omurice", ("omelet rice",)),
        ],
        "Mains & snacks": [
            ("tempura", ("Japanese battered seafood and vegetables",)), ("tonkatsu", ("Japanese pork cutlet",)),
            ("chicken katsu", ("Japanese chicken cutlet",)), ("karaage", ("Japanese fried chicken",)),
            ("teriyaki", ("teriyaki meat",)), ("yakitori", ("grilled chicken skewers",)),
            ("takoyaki", ("octopus balls",)), ("okonomiyaki", ("Japanese savory pancake",)),
            ("gyoza", ("Japanese dumplings",)), ("miso soup", ()),
            ("chawanmushi", ("steamed egg custard",)), ("edamame", ("soybeans",)),
        ],
        "Desserts": [
            ("mochi", ("rice cakes",)), ("dorayaki", ("red bean pancakes",)),
            ("matcha ice cream", ("green tea ice cream",)), ("taiyaki", ("fish-shaped pastry",)),
        ],
    },
    "Korean": {
        "Rice & noodles": [
            ("bibimbap", ("Korean mixed rice",)), ("kimbap", ("gimbap", "Korean rice rolls")),
            ("japchae", ("Korean glass noodles",)), ("jajangmyeon", ("black bean noodles",)),
            ("naengmyeon", ("Korean cold noodles",)), ("tteokbokki", ("spicy rice cakes",)),
            ("kimchi fried rice", ("kimchi bokkeumbap",)),
        ],
        "Mains & soups": [
            ("Korean barbecue", ("Korean BBQ",)), ("bulgogi", ("Korean grilled beef",)),
            ("galbi", ("Korean short ribs",)), ("samgyeopsal", ("grilled pork belly",)),
            ("Korean fried chicken", ()), ("kimchi stew", ("kimchi jjigae",)),
            ("soft tofu stew", ("sundubu jjigae",)), ("army stew", ("budae jjigae",)),
            ("seaweed soup", ("miyeok guk",)), ("samgyetang", ("ginseng chicken soup",)),
            ("kimchi", ("fermented cabbage",)), ("Korean pancakes", ("jeon", "pajeon")),
            ("mandu", ("Korean dumplings",)),
        ],
    },
    "Indian": {
        "Curries & mains": [
            ("curry", ("Indian curry",)), ("butter chicken", ("murgh makhani",)),
            ("chicken tikka masala", ()), ("chicken curry", ()), ("lamb curry", ()),
            ("fish curry", ()), ("vindaloo", ()), ("korma", ()),
            ("saag paneer", ("palak paneer",)), ("paneer tikka", ()),
            ("chana masala", ("chickpea curry",)), ("dal", ("daal", "lentil curry")),
            ("dal makhani", ()), ("aloo gobi", ("potato cauliflower curry",)),
            ("baingan bharta", ("roasted eggplant curry",)), ("tandoori chicken", ()),
        ],
        "Rice & breads": [
            ("biryani", ("Indian spiced rice",)), ("pulao", ("pilaf",)),
            ("naan", ("Indian flatbread",)), ("roti", ("chapati",)),
            ("paratha", ("layered Indian flatbread",)), ("dosa", ("South Indian crepe",)),
            ("idli", ("steamed rice cakes",)), ("uttapam", ("South Indian savory pancake",)),
        ],
        "Snacks & desserts": [
            ("samosa", ("Indian savory pastry",)), ("pakora", ("bhaji", "Indian fritters")),
            ("chaat", ("Indian street snack",)), ("pani puri", ("golgappa",)),
            ("vada", ("medu vada",)), ("gulab jamun", ()),
            ("jalebi", ()), ("kheer", ("Indian rice pudding",)),
            ("rasgulla", ("rosogolla",)), ("kulfi", ("Indian ice cream",)),
        ],
    },
    "Southeast Asian": {
        "Noodles & soups": [
            ("pad thai", ("Thai stir-fried noodles",)), ("pad see ew", ("Thai soy sauce noodles",)),
            ("drunken noodles", ("pad kee mao",)), ("pho", ("Vietnamese noodle soup",)),
            ("bun bo hue", ("Vietnamese spicy noodle soup",)), ("laksa", ("Southeast Asian curry noodle soup",)),
            ("khao soi", ("Northern Thai curry noodles",)), ("boat noodles", ()),
            ("tom yum soup", ("tom yam",)), ("tom kha soup", ("Thai coconut soup",)),
        ],
        "Rice & mains": [
            ("Thai green curry", ()), ("Thai red curry", ()), ("massaman curry", ()),
            ("pineapple fried rice", ()), ("nasi goreng", ("Indonesian fried rice",)),
            ("nasi lemak", ("Malaysian coconut rice",)), ("Hainanese chicken rice", ()),
            ("Thai basil chicken", ("pad kra pao",)), ("satay", ("grilled meat skewers",)),
            ("rendang", ("Indonesian beef stew",)), ("adobo", ("Filipino adobo",)),
            ("sinigang", ("Filipino sour soup",)), ("lechon", ("Filipino roast pork",)),
            ("sisig", ()), ("beef lok lak", ("Cambodian shaking beef",)),
        ],
        "Snacks & salads": [
            ("fresh spring rolls", ("Vietnamese summer rolls", "goi cuon")),
            ("banh mi", ("Vietnamese sandwich",)), ("papaya salad", ("som tam",)),
            ("larb", ("Thai minced meat salad",)), ("roti canai", ("Malaysian flatbread",)),
            ("lumpia", ("Filipino spring rolls",)), ("mango sticky rice", ()),
        ],
    },
    "Middle Eastern & North African": {
        "Mains": [
            ("shawarma", ("doner-style meat wrap",)), ("kebab", ("kabob", "grilled meat skewers")),
            ("kofta", ("kefta", "minced meat kebab")), ("falafel", ("chickpea fritters",)),
            ("hummus", ("chickpea dip",)), ("baba ganoush", ("eggplant dip",)),
            ("shakshuka", ("eggs in tomato sauce",)), ("tagine", ("Moroccan stew",)),
            ("couscous", ("North African couscous",)), ("mansaf", ()),
            ("kabsa", ("spiced meat and rice",)), ("maqluba", ("upside-down rice",)),
            ("koshari", ("Egyptian rice lentil pasta",)), ("fatteh", ()),
        ],
        "Breads & small plates": [
            ("pita bread", ("flatbread",)), ("manakish", ("manakeesh",)),
            ("lahmacun", ("Turkish flatbread",)), ("tabbouleh", ("parsley salad",)),
            ("fattoush", ("bread salad",)), ("stuffed grape leaves", ("dolma", "warak enab")),
            ("muhammara", ("red pepper dip",)), ("labneh", ("strained yogurt",)),
            ("kibbeh", ()), ("borek", ("savory filled pastry",)),
        ],
        "Desserts": [
            ("baklava", ()), ("kunafa", ("knafeh",)), ("halva", ("halwa",)),
            ("basbousa", ("semolina cake",)), ("Turkish delight", ("lokum",)),
        ],
    },
    "Italian & European": {
        "Pasta, rice & breads": [
            ("pizza", ("Italian pizza",)), ("pasta", ("Italian pasta",)),
            ("spaghetti", ()), ("carbonara", ("pasta carbonara",)),
            ("lasagna", ("lasagne",)), ("ravioli", ()), ("gnocchi", ()),
            ("risotto", ("Italian rice",)), ("polenta", ()),
            ("focaccia", ("Italian flatbread",)), ("bruschetta", ("tomato toast",)),
        ],
        "Mains & soups": [
            ("chicken parmesan", ("chicken parmigiana",)), ("eggplant parmesan", ("melanzane parmigiana",)),
            ("osso buco", ()), ("veal cutlet", ("schnitzel",)),
            ("beef stew", ()), ("goulash", ("Hungarian stew",)),
            ("beef bourguignon", ()), ("coq au vin", ()),
            ("ratatouille", ()), ("bouillabaisse", ("French seafood stew",)),
            ("French onion soup", ()), ("minestrone", ("Italian vegetable soup",)),
            ("gazpacho", ("cold tomato soup",)), ("paella", ("Spanish rice dish",)),
            ("Spanish tortilla", ("potato omelet",)), ("fish and chips", ()),
            ("shepherd's pie", ("cottage pie",)), ("bangers and mash", ()),
        ],
        "Small plates & desserts": [
            ("Greek salad", ("horiatiki",)), ("caprese salad", ()),
            ("croquettes", ()), ("patatas bravas", ()), ("calamari", ("fried squid",)),
            ("tiramisu", ()), ("cheesecake", ()), ("creme brulee", ("crème brûlée",)),
            ("panna cotta", ()), ("cannoli", ()), ("macarons", ("French macarons",)),
            ("gelato", ("Italian ice cream",)), ("churros", ()),
        ],
    },
    "Latin American & Caribbean": {
        "Mains": [
            ("tacos", ("Mexican tacos",)), ("burrito", ()), ("quesadilla", ()),
            ("enchiladas", ()), ("tamales", ("tamale",)), ("fajitas", ()),
            ("chile relleno", ("stuffed chile",)), ("mole", ("Mexican mole",)),
            ("pozole", ("Mexican hominy soup",)), ("menudo", ("Mexican tripe soup",)),
            ("birria", ("Mexican meat stew",)), ("tostadas", ()),
            ("arepas", ("arepa",)), ("empanadas", ("empanada",)),
            ("ceviche", ("citrus marinated seafood",)), ("lomo saltado", ("Peruvian beef stir-fry",)),
            ("arroz con pollo", ("chicken and rice",)), ("ropa vieja", ("Cuban shredded beef",)),
            ("jerk chicken", ("Jamaican jerk chicken",)), ("oxtail stew", ()),
            ("feijoada", ("Brazilian bean stew",)), ("churrasco", ("Latin grilled steak",)),
        ],
        "Sides & snacks": [
            ("nachos", ()), ("guacamole", ("avocado dip",)), ("salsa", ("Mexican salsa",)),
            ("elote", ("Mexican street corn",)), ("pupusas", ("pupusa",)),
            ("plantains", ("fried plantains", "tostones", "maduros")),
            ("rice and beans", ()), ("yuca fries", ("cassava fries",)),
        ],
        "Desserts": [
            ("flan", ("caramel custard",)), ("tres leches cake", ()),
            ("alfajores", ()), ("brigadeiro", ()), ("rice pudding", ("arroz con leche",)),
        ],
    },
    "American & Canadian": {
        "Mains": [
            ("hamburger", ("burger", "cheeseburger")), ("hot dog", ()),
            ("fried chicken", ()), ("chicken wings", ("buffalo wings",)),
            ("barbecue ribs", ("BBQ ribs",)), ("pulled pork", ()),
            ("steak", ("grilled steak",)), ("meatloaf", ()),
            ("macaroni and cheese", ("mac and cheese",)), ("chili", ("chili con carne",)),
            ("clam chowder", ()), ("lobster roll", ()), ("crab cakes", ()),
            ("grilled cheese", ("grilled cheese sandwich",)), ("club sandwich", ()),
            ("submarine sandwich", ("sub sandwich", "hoagie", "hero sandwich")),
            ("poutine", ("fries with gravy and cheese curds",)),
        ],
        "Breakfast & sides": [
            ("pancakes", ("hotcakes",)), ("waffles", ()), ("French toast", ()),
            ("eggs benedict", ()), ("omelette", ("omelet",)),
            ("scrambled eggs", ()), ("fried eggs", ()), ("breakfast burrito", ()),
            ("biscuits and gravy", ()), ("hash browns", ("potato hash",)),
            ("oatmeal", ("porridge",)), ("granola", ()), ("cereal", ()),
            ("french fries", ("fries", "chips")), ("onion rings", ()),
            ("mashed potatoes", ()), ("cornbread", ()), ("coleslaw", ()),
        ],
        "Desserts": [
            ("apple pie", ()), ("pumpkin pie", ()), ("pecan pie", ()),
            ("brownies", ("chocolate brownie",)), ("cookies", ("biscuits",)),
            ("cupcakes", ("cup cakes",)), ("donuts", ("doughnuts",)),
            ("ice cream", ()), ("banana split", ()), ("milkshake", ()),
        ],
    },
    "General": {
        "Soups & salads": [
            ("soup", ("bowl of soup",)), ("tomato soup", ()), ("vegetable soup", ()),
            ("chicken soup", ()), ("lentil soup", ()), ("pumpkin soup", ()),
            ("salad", ("mixed salad",)), ("Caesar salad", ()), ("cobb salad", ()),
            ("fruit salad", ()), ("bean salad", ()), ("potato salad", ()),
            ("pasta salad", ()), ("seaweed salad", ()),
        ],
        "Seafood & meat": [
            ("grilled fish", ("cooked fish",)), ("fried fish", ()),
            ("grilled salmon", ("salmon fillet",)), ("tuna steak", ()),
            ("shrimp", ("prawns",)), ("grilled shrimp", ("grilled prawns",)),
            ("lobster", ()), ("crab", ()), ("mussels", ()), ("oysters", ()),
            ("scallops", ()), ("roast chicken", ()), ("grilled chicken", ()),
            ("pork chop", ()), ("lamb chops", ()), ("roast beef", ()),
            ("meatballs", ()), ("sausage", ()),
        ],
        "Vegetables & plant foods": [
            ("roasted vegetables", ()), ("grilled vegetables", ()),
            ("steamed vegetables", ()), ("stir-fried vegetables", ()),
            ("roasted potatoes", ()), ("baked potato", ()),
            ("corn on the cob", ()), ("green beans", ()), ("broccoli", ()),
            ("roasted cauliflower", ()), ("stuffed peppers", ()),
            ("tofu", ("bean curd",)), ("tempeh", ()),
        ],
        "Breads & snacks": [
            ("bread", ("loaf of bread",)), ("toast", ()), ("bagel", ()),
            ("croissant", ()), ("pretzel", ()), ("muffin", ()),
            ("sandwich", ()), ("wrap", ("filled wrap",)),
            ("popcorn", ()), ("potato chips", ("crisps",)), ("crackers", ()),
            ("nuts", ("mixed nuts",)), ("cheese plate", ("cheese board",)),
        ],
        "Fruit & desserts": [
            ("fresh fruit", ("fruit plate",)), ("fruit bowl", ()),
            ("berries", ("mixed berries",)), ("watermelon", ()),
            ("pineapple", ()), ("mango", ()), ("banana", ()),
            ("cake", ("slice of cake",)), ("chocolate cake", ()),
            ("carrot cake", ()), ("red velvet cake", ()),
            ("pudding", ()), ("custard", ()), ("fruit tart", ()),
            ("dough pastry", ("sweet pastry",)),
        ],
        "Drinks": [
            ("coffee", ("cup of coffee",)), ("espresso", ()), ("latte", ("cafe latte",)),
            ("cappuccino", ()), ("tea", ("cup of tea",)), ("bubble tea", ("boba tea",)),
            ("hot chocolate", ()), ("fruit juice", ("juice",)), ("smoothie", ()),
            ("lemonade", ()), ("soft drink", ("soda",)), ("water", ("bottled water",)),
        ],
    },
}


def _build_vocabulary():
    vocabulary = {}
    for cuisine, categories in FOOD_GROUPS.items():
        for category, dishes in categories.items():
            for name, aliases in dishes:
                key = name.casefold()
                if key in vocabulary:
                    raise ValueError(f"Duplicate canonical food label: {name}")
                descriptions = tuple(dict.fromkeys((name, *aliases)))
                vocabulary[key] = {
                    "name": name,
                    "aliases": descriptions,
                    "cuisine": cuisine,
                    "category": category,
                }
    return vocabulary


FOOD_CANDIDATES = _build_vocabulary()
