# To-Do

## Recipes to add

- [ ] **Chocolate Chess Pie** — `originals/PXL_20260523_110507122.RAW-01.COVER.jpg` — magazine source (Celebrate). Not urgent.

## Recipes needing manual review (`needs-manual-review`)

- [ ] **Ball Real Fruit Jam** (`wc-kitchen.ball-realfruit-low-or-no-sugar-jam`) — steps 1–3 not in image; only tail of step 4 visible. Add from Ball/freshpreserving.com source.
- [ ] **Beginner's Guide to French Macarons** (`wc-kitchen.beginners-guide-to-french-macarons`) — only tips/notes pages photographed; ingredient quantities not visible. Look up at source URL.
- [ ] **Chocolate Biscotti** (`wc-kitchen.chocolate-biscotti`) — baking powder discrepancy: ingredients say ½ tsp, step 4 says 1 tbsp. Verify at source URL.
- [ ] **French Macarons** (`wc-kitchen.french-macarons`) — only page 1 of 3 captured; steps are incomplete. Needs remaining pages or source URL lookup.
- [ ] **Ground Turkey and Potato Skillet** (`wc-kitchen.ground-turkey-and-potato-skillet`) — instructions cut off mid-step 2; steps 3+ (combining turkey with potatoes and sauce) not captured.
- [ ] **Quick and Easy Red Lentil Dahl** (`wc-kitchen.quick-and-easy-red-lentil-dahl`) — page 1 of 2; spinach and lemon steps (step 4+) not captured.
- [ ] **Sweet Pickled Radishes** (`wc-kitchen.sweet-pickled-radishes`) — ground spice type unknown; amount (½ tsp) readable from image edge but variety not legible. Look up at marisamoore.com.
- [ ] **Toum** (`wc-kitchen.toum`) — steps 1–2 visible; remaining steps cut off by NYT paywall notice. Verify full method at NYT Cooking.
- [ ] **Vegetarian Lentil Tortilla Soup** (`wc-kitchen.vegetarian-lentil-tortilla-soup`) — only ingredients page photographed; instructions missing. Find at peasandcrayons.com.
- [ ] **Yule Log Cake** (`wc-kitchen.yule-log-cake`) — only ganache/assembly steps visible (page 2); cake batter, rolling, and filling steps missing.
- [ ] **Shakshuka With Feta** (`wc-kitchen.shakshuka-with-feta`) — image cut off below feta; eggs (qty unknown), cilantro, and hot sauce are in steps but not visible in ingredients. Verify at NYT Cooking (Melissa Clark).
- [ ] **Dairy Free Quiche Lorraine** (`wc-kitchen.dairy-free-quiche-lorraine`) — steps 5+ cut off; filling/baking method missing. Find source URL to complete.

## In progress (`recipes/in-progress/`)

Incomplete drafts excluded from CI (validate, render, index). Move to `recipes/` when ready.

- [ ] **Easy Slow Cooker Beef Stew** (`recipes/in-progress/wc-kitchen.easy-slow-cooker-beef-stew.yaml`) — page 1 of 2; all steps are on the missing second page.
- [ ] **Meatloaf** (`recipes/in-progress/wc-kitchen.meatloaf.yaml`) — blurry handwritten notecard; "molasses" may actually say "applesauce" — verify in person. Worcestershire and applesauce/molasses quantities not legible.

## Other issues to verify

- [ ] **Gochujang Roasted Carrots** (`wc-kitchen.gochujang-roasted-carrots`) — cook time conflict: header says 55 min, step times don't add up. Verify against original source.

## Tooling (`recipes/in-progress/`)

- [x] Document `recipes/in-progress/` in `notes.md`
- [ ] Add `list_draft_recipe_ids()` in `paths.py` and `recipe validate --drafts` for validating in-progress files while working on them
- [ ] Update `_is_referenced_in_recipes` in `status.py` to scan `recipes/**/*.yaml` so originals referenced only from drafts don't show as unreferenced
- [ ] Update other flat `recipes/*.yaml` globs (`extract --pending`, `rename_originals.py`) to include `recipes/in-progress/` where reference lookups matter
- [ ] **Optional:** Stop committing `site/` and `pdfs/` — let CI generate and deploy; commit only `recipes/` (and `originals/` as needed). Bigger workflow change: update `.gitignore`, README/USER_GUIDE, and binder workflow (print PDFs from CI artifacts or local `recipe pdf` on demand).
- [ ] YAML (notes.md) notes that group headers in ingredients (plain-string values like `- Sauce:`) are allowed; they are ignored at render time. | ideally, these would render, as they improve usability in recipe.
