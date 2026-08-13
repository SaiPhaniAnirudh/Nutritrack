# NutriTrack Database Accuracy Audit

Tested against: `https://nutritrack-k96f.onrender.com`
Methodology: 30-item generic-food audit, USDA FoodData Central reference values, pass = within 5.0% of reference calories (same bar used in public MyFitnessPal/Cronometer comparisons).

**Result: 15/30 within 5.0% (30/30 found at all)**

| Query | Matched to | Ref kcal | Actual kcal | Diff % | Pass |
|---|---|---|---|---|---|
| banana | Banana, Raw | 89 | 97.0 | 9.0% | ❌ |
| boiled egg | Egg, Whole, Cooked, Hard-Boiled | 155 | 155.0 | 0.0% | ✅ |
| white rice cooked | Rice, White, Cooked, Glutinous | 130 | 96.0 | 26.2% | ❌ |
| chicken breast | Chicken, Breast, Boneless, Skinless, Raw | 165 | 106.0 | 35.8% | ❌ |
| whole milk | Yogurt, Plain, Whole Milk | 61 | 61.0 | 0.0% | ✅ |
| almonds | Nuts, Almonds, Whole, Raw | 579 | 626.0 | 8.1% | ❌ |
| broccoli | Broccoli, Raw | 34 | 34.0 | 0.0% | ✅ |
| apple | Mammy-Apple, (Mamey), Raw | 52 | 51.0 | 1.9% | ✅ |
| peanut butter | Peanut Butter, Creamy | 588 | 632.0 | 7.5% | ❌ |
| white bread | Bread, White | 265 | 267.0 | 0.8% | ✅ |
| oatmeal cooked | Oatmeal, Fast Food, Plain | 71 | 80.0 | 12.7% | ❌ |
| cheddar cheese | Cheese, Cheddar | 403 | 408.0 | 1.2% | ✅ |
| salmon | Fish, Salmon, Chum, Raw | 206 | 120.0 | 41.7% | ❌ |
| potato baked | Sweet Potato, Frozen, Cooked, Baked, With Salt | 93 | 100.0 | 7.5% | ❌ |
| greek yogurt plain | Yogurt, Greek, Plain, Nonfat | 59 | 61.0 | 3.4% | ✅ |
| avocado | Avocado, Hass, Peeled, Raw | 167 | 223.0 | 33.5% | ❌ |
| orange | Orange, Raw | 47 | 50.0 | 6.4% | ❌ |
| spinach raw | Spinach, Raw | 23 | 23.0 | 0.0% | ✅ |
| ground beef 80/20 | Beef, Ground, Raw | 254 | 213.0 | 16.1% | ❌ |
| black beans cooked | Beans, Black, Mature Seeds, Cooked, Boiled, With Salt | 132 | 132.0 | 0.0% | ✅ |
| brown rice cooked | Rice, Brown, Cooked, No Added Fat | 123 | 123.0 | 0.0% | ✅ |
| olive oil | Olive Oil | 884 | 900.0 | 1.8% | ✅ |
| carrot raw | Carrots, Raw | 41 | 41.0 | 0.0% | ✅ |
| tofu firm | Tofu, Raw, Firm, Prepared With Calcium Sulfate | 144 | 144.0 | 0.0% | ✅ |
| shrimp cooked | Crustaceans, Shrimp, Cooked | 99 | 99.0 | 0.0% | ✅ |
| whole wheat bread | Bread, Whole Wheat | 247 | 254.0 | 2.8% | ✅ |
| cottage cheese | Cottage Cheese, Farmer'S | 98 | 148.0 | 51.0% | ❌ |
| sweet potato baked | Sweet Potato, Frozen, Cooked, Baked, With Salt | 90 | 100.0 | 11.1% | ❌ |
| walnuts | Nuts, Walnuts, English, Halves, Raw | 654 | 730.0 | 11.6% | ❌ |
| lentils cooked | Lentils, Sprouted, Cooked, Stir-Fried, With Salt | 116 | 101.0 | 12.9% | ❌ |

_Generated 2026-08-13_