# Candidate list for batch alias generation. Organized by category for
# maintainability. Indian cuisine is weighted heavily per the app's stated
# specialization (README: "80+ regional foods").

FRUITS = [
    "banana", "apple", "orange", "grapes", "watermelon", "pineapple", "mango",
    "strawberry", "blueberry", "raspberry", "blackberry", "kiwi", "pear",
    "peach", "plum", "cherry", "pomegranate", "papaya", "guava", "fig",
    "dates", "raisins", "cantaloupe", "honeydew melon", "grapefruit",
    "lemon", "lime", "coconut", "avocado", "apricot", "lychee",
    "starfruit", "dragon fruit", "passion fruit", "custard apple",
    "jackfruit", "persimmon", "cranberry", "gooseberry", "mulberry",
    "tangerine", "nectarine", "prune", "currant", "elderberry",
]

VEGETABLES = [
    "broccoli", "spinach", "carrot", "potato", "sweet potato", "tomato",
    "cucumber", "lettuce", "cabbage", "cauliflower", "onion", "garlic",
    "ginger", "bell pepper", "zucchini", "eggplant", "green beans", "peas",
    "corn", "mushroom", "asparagus", "beetroot", "radish", "celery",
    "kale", "brussels sprouts", "pumpkin", "squash", "okra", "artichoke",
    "bok choy", "leek", "turnip", "parsnip", "fennel", "arugula",
    "swiss chard", "collard greens", "watercress", "bamboo shoots",
    "bean sprouts", "jalapeno", "chili pepper", "scallion", "shallot",
    "bitter gourd", "bottle gourd", "ridge gourd", "drumstick vegetable",
    "taro root", "yam",
]

PROTEINS = [
    "chicken breast", "chicken thigh", "chicken drumstick", "chicken wing",
    "ground beef", "beef steak", "beef brisket", "pork chop", "pork belly",
    "bacon", "turkey breast", "ground turkey", "salmon", "tuna", "shrimp",
    "tilapia", "cod", "halibut", "mackerel", "sardines", "trout", "catfish",
    "boiled egg", "fried egg", "scrambled eggs", "egg whites", "quail egg",
    "tofu", "tempeh", "seitan", "lamb", "lamb chop", "ham", "sausage",
    "chorizo", "crab", "lobster", "duck", "venison", "bison", "goat meat",
    "rabbit meat", "octopus", "squid", "mussels", "clams", "oysters",
    "scallops", "anchovies", "beef liver", "chicken liver",
]

DAIRY = [
    "whole milk", "skim milk", "2% milk", "almond milk", "soy milk",
    "oat milk", "coconut milk", "greek yogurt plain", "yogurt",
    "cheddar cheese", "mozzarella cheese", "cottage cheese", "cream cheese",
    "butter", "ghee", "sour cream", "heavy cream", "parmesan cheese",
    "feta cheese", "swiss cheese", "paneer", "condensed milk", "buttermilk",
    "ricotta cheese", "gouda cheese", "brie cheese", "blue cheese",
    "provolone cheese", "goat cheese", "half and half", "whipped cream",
    "custard", "flan",
]

GRAINS = [
    "white rice cooked", "brown rice cooked", "basmati rice", "jasmine rice",
    "quinoa cooked", "oatmeal cooked", "steel cut oats", "white bread",
    "whole wheat bread", "rye bread", "sourdough bread", "pasta cooked",
    "spaghetti cooked", "macaroni cooked", "couscous cooked", "barley cooked",
    "cornflakes", "granola", "bagel", "tortilla", "pita bread", "naan",
    "chapati", "roti", "brown bread", "cereal", "muesli", "buckwheat cooked",
    "millet cooked", "polenta", "grits", "rice noodles", "egg noodles",
    "udon noodles", "soba noodles", "vermicelli", "wheat flour",
    "cornmeal", "breadcrumbs", "crouton",
]

LEGUMES_NUTS = [
    "black beans cooked", "kidney beans cooked", "chickpeas cooked",
    "lentils cooked", "green peas", "pinto beans cooked", "navy beans cooked",
    "lima beans cooked", "split peas cooked", "edamame", "soybeans cooked",
    "peanuts", "almonds", "walnuts", "cashews", "pistachios", "pecans",
    "hazelnuts", "brazil nuts", "macadamia nuts", "pine nuts",
    "sunflower seeds", "chia seeds", "flax seeds", "pumpkin seeds",
    "sesame seeds", "hemp seeds", "peanut butter", "almond butter",
    "cashew butter", "hummus", "tahini",
]

FATS_OILS = [
    "olive oil", "coconut oil", "vegetable oil", "canola oil", "sesame oil",
    "mustard oil", "avocado oil", "sunflower oil", "peanut oil",
    "mayonnaise", "margarine", "lard", "shortening",
]

BEVERAGES = [
    "orange juice", "apple juice", "cranberry juice", "grape juice",
    "coffee black", "green tea", "black tea", "herbal tea", "chai tea",
    "coconut water", "soda", "diet soda", "energy drink", "beer",
    "red wine", "white wine", "whiskey", "vodka", "rum", "protein shake",
    "smoothie", "lassi", "buttermilk drink", "milkshake", "hot chocolate",
    "sports drink", "kombucha", "iced tea", "lemonade",
]

CONDIMENTS_SAUCES = [
    "ketchup", "mustard", "soy sauce", "barbecue sauce", "hot sauce",
    "salsa", "ranch dressing", "italian dressing", "vinaigrette",
    "worcestershire sauce", "teriyaki sauce", "fish sauce", "oyster sauce",
    "pesto", "marinara sauce", "alfredo sauce", "gravy", "honey",
    "maple syrup", "jam", "peanut sauce", "sriracha", "wasabi",
    "horseradish", "pickle relish", "cocktail sauce", "tartar sauce",
]

INDIAN_CUISINE = [
    "biryani", "chicken biryani", "veg biryani", "mutton biryani",
    "dosa", "masala dosa", "plain dosa", "rava dosa", "idli", "sambar",
    "dal", "dal tadka", "dal makhani", "dal fry", "paratha", "aloo paratha",
    "gobi paratha", "roti", "chapati", "naan", "garlic naan",
    "butter chicken", "chicken tikka masala", "paneer tikka",
    "palak paneer", "matar paneer", "paneer butter masala", "chole",
    "rajma", "chana masala", "aloo gobi", "baingan bharta", "bhindi masala",
    "pav bhaji", "vada pav", "samosa", "pakora", "onion bhaji", "poha",
    "upma", "khichdi", "curd rice", "lemon rice", "tamarind rice",
    "jeera rice", "vegetable pulao", "chicken curry", "mutton curry",
    "fish curry", "prawn curry", "egg curry", "tandoori chicken",
    "malai kofta", "kadhi", "raita", "papadum", "chutney",
    "mango pickle", "gulab jamun", "rasgulla", "jalebi", "kheer",
    "gajar halwa", "moong dal halwa", "ladoo", "besan ladoo", "barfi",
    "kulfi", "mango lassi", "sweet lassi", "masala chai", "filter coffee",
    "idiyappam", "uttapam", "medu vada", "rasam", "pongal",
    "bisi bele bath", "misal pav", "dhokla", "khaman", "thepla",
    "kachori", "chaat", "pani puri", "bhel puri", "sev puri",
    "dahi vada", "aloo tikki", "kathi roll", "frankie roll",
    "egg roll indian", "mysore pak", "sooji halwa", "poori", "bhatura",
    "kulcha", "missi roti", "makki di roti", "sarson da saag",
    "litti chokha", "dhansak", "vindaloo", "korma", "kofta curry",
    "shahi paneer", "chana chaat", "murgh malai tikka", "seekh kebab",
    "chicken 65", "hyderabadi biryani", "keema", "nihari", "haleem",
]

FAST_FOOD_SNACKS = [
    "pizza slice", "cheese pizza", "pepperoni pizza", "burger",
    "cheeseburger", "french fries", "hot dog", "fried chicken",
    "chicken nuggets", "taco", "burrito", "quesadilla", "nachos",
    "sushi roll", "california roll", "ramen", "fried rice", "spring roll",
    "potato chips", "popcorn", "pretzel", "chocolate bar", "cookie",
    "brownie", "cake slice", "cheesecake", "ice cream", "donut", "muffin",
    "croissant", "waffle", "pancake", "protein bar", "granola bar",
    "trail mix", "crackers", "beef jerky", "candy", "gummy bears",
    "chocolate chip cookie", "cinnamon roll",
]

MEALS_MISC = [
    "caesar salad", "greek salad", "cobb salad", "chicken sandwich",
    "grilled cheese sandwich", "club sandwich", "blt sandwich",
    "vegetable soup", "chicken soup", "tomato soup", "minestrone soup",
    "mac and cheese", "lasagna", "pad thai", "pho", "curry chicken",
    "stir fry vegetables", "omelette", "scrambled eggs", "french toast",
    "cereal with milk", "shepherds pie", "chili con carne", "beef stew",
    "fajitas", "enchiladas", "risotto", "paella", "gnocchi",
    "chicken parmesan", "fish and chips", "coleslaw", "potato salad",
    "egg salad", "chicken salad", "tuna salad", "deviled eggs",
    "stuffed peppers", "meatloaf", "meatballs", "kebab", "gyro",
    "falafel", "shawarma", "hummus plate", "tabbouleh", "baba ganoush",
    "dim sum", "dumplings", "spring rolls vietnamese", "bibimbap",
    "kimchi", "miso soup", "teriyaki chicken", "orange chicken",
    "general tso chicken", "kung pao chicken", "chow mein",
]

MEXICAN_ITALIAN_ASIAN = [
    "tacos al pastor", "carne asada", "chicken fajita bowl",
    "guacamole", "churros", "tamales", "pozole", "carnitas",
    "spaghetti bolognese", "fettuccine alfredo", "penne arrabbiata",
    "margherita pizza", "caprese salad", "bruschetta", "tiramisu",
    "gelato", "focaccia", "ravioli", "tortellini", "minestrone",
    "sweet and sour chicken", "beef and broccoli", "egg fried rice",
    "hot and sour soup", "wonton soup", "peking duck", "tempura",
    "yakitori", "gyoza", "katsu curry", "onigiri", "tonkatsu",
]

BREAKFAST_BAKED = [
    "toast with butter", "avocado toast", "bacon and eggs",
    "breakfast burrito", "yogurt parfait", "overnight oats",
    "banana bread", "cornbread", "biscuit", "scone", "danish pastry",
    "english muffin", "hash browns", "grits with butter",
    "breakfast sausage", "breakfast burrito bowl", "eggs benedict",
    "shakshuka", "congee",
]

ALL_FOODS = (
    FRUITS + VEGETABLES + PROTEINS + DAIRY + GRAINS + LEGUMES_NUTS +
    FATS_OILS + BEVERAGES + CONDIMENTS_SAUCES + INDIAN_CUISINE +
    FAST_FOOD_SNACKS + MEALS_MISC + MEXICAN_ITALIAN_ASIAN + BREAKFAST_BAKED
)

if __name__ == "__main__":
    print(f"Total candidate foods: {len(ALL_FOODS)}")
    print(f"\nBreakdown:")
    for name, lst in [
        ("Fruits", FRUITS), ("Vegetables", VEGETABLES),
        ("Proteins", PROTEINS), ("Dairy", DAIRY), ("Grains", GRAINS),
        ("Legumes/Nuts", LEGUMES_NUTS), ("Fats/Oils", FATS_OILS),
        ("Beverages", BEVERAGES), ("Condiments", CONDIMENTS_SAUCES),
        ("Indian Cuisine", INDIAN_CUISINE), ("Fast Food/Snacks", FAST_FOOD_SNACKS),
        ("Meals/Misc", MEALS_MISC), ("Mexican/Italian/Asian", MEXICAN_ITALIAN_ASIAN),
        ("Breakfast/Baked", BREAKFAST_BAKED),
    ]:
        print(f"  {name:<25} {len(lst):>4}")
