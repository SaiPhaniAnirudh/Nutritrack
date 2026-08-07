# NutriTrack Database Accuracy Audit

Tested against: `https://nutritrack-k96f.onrender.com`
Methodology: 30-item generic-food audit, USDA FoodData Central reference values, pass = within 5.0% of reference calories (same bar used in public MyFitnessPal/Cronometer comparisons).

**Result: 27/30 within 5.0% (30/30 found at all)**

| Query | Matched to | Ref kcal | Actual kcal | Diff % | Pass |
|---|---|---|---|---|---|
| banana | Bananas, Raw | 89 | 89.0 | 0.0% | ✅ |
| boiled egg | Egg, Whole, Cooked, Hard-Boiled | 155 | 155.0 | 0.0% | ✅ |
| white rice cooked | Rice, White, Long-Grain, Regular, Cooked, Enriched, With Salt | 130 | 130.0 | 0.0% | ✅ |
| chicken breast | Chicken, Broilers Or Fryers, Breast, Meat Only, Cooked, Roasted | 165 | 165.0 | 0.0% | ✅ |
| whole milk | Milk, Whole, 3.25% Milkfat, With Added Vitamin D | 61 | 61.0 | 0.0% | ✅ |
| almonds | Nuts, Almonds | 579 | 579.0 | 0.0% | ✅ |
| broccoli | Broccoli, Raw | 34 | 34.0 | 0.0% | ✅ |
| apple | Apples, Raw, With Skin (Includes Foods For Usda'S Food Distribution Program) | 52 | 52.0 | 0.0% | ✅ |
| peanut butter | Peanut Butter, Creamy | 588 | 632.0 | 7.5% | ❌ |
| white bread | Bread, White, Commercially Prepared (Includes Soft Bread Crumbs) | 265 | 266.0 | 0.4% | ✅ |
| oatmeal cooked | Cereals, Oats, Regular And Quick And Instant, Unenriched, Cooked With Water (Includes Boiling And Microwaving), With Salt | 71 | 71.0 | 0.0% | ✅ |
| cheddar cheese | Cheese, Cheddar | 403 | 408.0 | 1.2% | ✅ |
| salmon | Fish, Salmon, Atlantic, Farmed, Cooked, Dry Heat | 206 | 206.0 | 0.0% | ✅ |
| potato baked | Potatoes, Baked, Flesh, With Salt | 93 | 93.0 | 0.0% | ✅ |
| greek yogurt plain | Yogurt, Greek, Plain, Nonfat | 59 | 61.0 | 3.4% | ✅ |
| avocado | Avocados, Raw, All Commercial Varieties | 167 | 160.0 | 4.2% | ✅ |
| orange | Oranges, Raw, All Commercial Varieties | 47 | 47.0 | 0.0% | ✅ |
| spinach raw | Spinach, Raw | 23 | 23.0 | 0.0% | ✅ |
| ground beef 80/20 | Beef, Ground, 80% Lean Meat / 20% Fat, Loaf, Cooked, Baked | 254 | 254.0 | 0.0% | ✅ |
| black beans cooked | Beans, Black, Mature Seeds, Cooked, Boiled, With Salt | 132 | 132.0 | 0.0% | ✅ |
| brown rice cooked | Rice, Brown, Cooked, No Added Fat | 123 | 123.0 | 0.0% | ✅ |
| olive oil | Oil, Olive, Salad Or Cooking | 884 | 884.0 | 0.0% | ✅ |
| carrot raw | Carrots, Raw | 41 | 41.0 | 0.0% | ✅ |
| tofu firm | Tofu, Raw, Firm, Prepared With Calcium Sulfate | 144 | 144.0 | 0.0% | ✅ |
| shrimp cooked | Crustaceans, Shrimp, Cooked | 99 | 99.0 | 0.0% | ✅ |
| whole wheat bread | Bread, Whole-Wheat, Commercially Prepared | 247 | 252.0 | 2.0% | ✅ |
| cottage cheese | Cottage Cheese, Full Fat, Large Or Small Curd | 98 | 103.0 | 5.1% | ❌ |
| sweet potato baked | Sweet Potato, Cooked, Baked In Skin, Flesh, With Salt | 90 | 90.0 | 0.0% | ✅ |
| walnuts | Nuts, Walnuts, English, Halves, Raw | 654 | 730.0 | 11.6% | ❌ |
| lentils cooked | Lentils, Mature Seeds, Cooked, Boiled, With Salt | 116 | 114.0 | 1.7% | ✅ |

_Generated 2026-08-07_