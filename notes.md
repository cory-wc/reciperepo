# YAML conventions & reference

Rules for recipe file content in this collection. For setup, CLI commands, and add/update/remove workflows, see [README.md](README.md). For a non-technical walkthrough, see [USER_GUIDE.md](USER_GUIDE.md). Doc roles: [docs/documentation.md](docs/documentation.md).

---

## Naming

- **Namespace:** `wc-kitchen.{slug}` for `recipe_uuid` and filename
- **Slug:** kebab-case from title (`Banana Bread` → `banana-bread`)
- **Example file:** `wc-kitchen.banana-bread.yaml`

Parenthetical disambiguation when titles collide: `Thai Peanut Sauce (Eat With Clarity)` vs `Thai Peanut Sauce (Jessica in the Kitchen)`.

---

## YAML structure (strict ORF)

- **Ingredients:** dict-key form (`- sugar:` with nested `amounts`), never `ingredient:` field
- **Authors:** use `source_authors:` (list), not `author:`
- **Web sources:** `source_url:` with the **full recipe page URL**
- **File/photo sources:** `X-original-source: ../originals/...` (from top-level `recipes/`)
- **Both:** web recipes you printed can have `source_url` **and** `X-original-source` (screenshot)

<!-- See to-do.md -->
Group headers in ingredients (plain-string values like `- Sauce:`) are allowed; they are ignored at render time.

---

## Metadata

Recipe files carry **core ORF fields** (`recipe_uuid`, `recipe_name`, `yields`, `ingredients`, `steps`) plus **extension fields** prefixed with `X-`. Taxonomy uses two structured blocks:

- **`X-categories`** — what kind of dish it is and when you serve it
- **`X-tags`** — how it's made, dietary fit, and descriptive facets

All taxonomy values use **lowercase snake_case** in YAML lists.

### Target shape

```yaml
X-categories:
  dish_type:
    - main
  meal_type:
    - dinner
  meal_role:
    - one_dish_meal

X-tags:
  cuisine:
    - german
  dietary:
    - vegetarian
  method:
    - stovetop
  context:
    - weeknight
    - leftovers_friendly
  season:
    - fall
  primary_ingredient:
    - potatoes
    - bacon
  flavor_profile:
    - savory
    - hearty
```

Each key holds a **YAML list**. Multiple values are allowed on all keys unless noted below.

### Legacy metadata (migration in progress)

Many files still use the older flat fields. During migration, **`recipe audit-metadata` checks legacy fields** until a recipe is converted.

| Legacy field | Replaced by |
|--------------|-------------|
| `X-category` (flat list) | `X-categories` (`dish_type`, `meal_type`, …) |
| `X-tags` (flat freeform list) | structured `X-tags` (`method`, `context`, …) |
| `X-dietary` (top-level list) | `X-tags.dietary` |
| `X-cuisine` (top-level string) | `X-tags.cuisine` |
| `author` | `source_authors` |
| `X-author`, `X-source-author` | `source_authors` |
| `X-equipment` | `equipment` |
| `X-method` | `X-tags.method` |
| `X-source-description` | `description` |
| `X-calories` | `X-nutrition.calories` |
| `X-hands_on_time` | `X-active_time` (when active time missing) |
| `X-tips`, `X-notes`, `X-handwritten-*` | `notes` |
| `X-tags.planning` | `X-tags.context` (`make_ahead`, `meal_prep`, `leftovers_friendly`, `freezer-friendly`) |
| `X-show`, `X-episode`, `X-publisher`, `X-copyright`, `X-published`, `X-source-publication`, `X-source-updated`, `X-attribution` | *(drop)* |

When editing a recipe, prefer the target shape above. Remove legacy fields once converted.

**Confirmed mapping rules:**

| Situation | Target |
|-----------|--------|
| IP black beans, Instant Pot farro | `dish_type: [component, side]` |
| Pasta e Piselli and similar pasta mains | `dish_type: [pasta]` only (not `one_dish`) |
| Legacy flat tags that repeat the recipe name (`sloppy joes`, `swedish meatballs`) | Drop — already in `recipe_name`; use structured tags for filterable facets only |
| Unclassified flat tags (`gravy`, dish descriptors) | Drop — do not map to `flavor_profile` unless explicitly curated |
| Tags redundant with `meal_type` (e.g. `breakfast` when `meal_type: [breakfast]`) | Drop |
| Legacy `X-category: seafood` | `dish_type: [main]` + `X-tags.cuisine: [seafood]` |
| Legacy `Appetizer` (category or tag) | `dish_type: [side]` |

---

## `X-categories`

### `dish_type`

What format the recipe is. **Prefer 1–2 values** per recipe (guidance only — not enforced). Pick the best-fit primary type; add a second only when two buckets are genuinely equal (e.g. `component` + `side` for black beans you both prep and serve alone). More than two is allowed but should be rare — use `meal_type`, `method`, or `primary_ingredient` for extra context instead of stacking `dish_type`.

| Value | Use for |
|-------|---------|
| `soup` | Soups, stews, chowders, chili |
| `salad` | Green, bean, pasta, grain salads |
| `pasta` | Pasta as the main format |
| `main` | Generic entrées (stir-fry, pan-seared protein, bratkartoffeln) |
| `one_dish` | Casseroles, skillets, sheet-pan roasts, pot pies, lasagna |
| `bowl` | Burrito bowls, buddha bowls, composed grain bowls |
| `burger` | Burgers, sandwiches, wraps, and other handheld mains |
| `side` | Finished sides served alongside a meal |
| `sauce` | Sauces, condiments, dips, dressings |
| `component` | Prep/base for other dishes (farro method, IP black beans, pie dough) |
| `preserve` | Jam, relish, pickles, canning |
| `bread` | Loaves, muffins, biscuits, quick breads |
| `dessert` | Cakes, cookies, pastries, crisps |
| `breakfast_bake` | Quiche, baked oatmeal, frittata-style bakes |
| `beverage` | Cocktails, hot chocolate mix, etc. |
| `reference` | Binder index pages only |

**Disambiguation:**

| Type | Rule of thumb | Examples |
|------|---------------|----------|
| `component` | Building block or technique; usually paired with something else | Instant Pot farro, IP black beans, pie dough |
| `side` | Served as its own side at the table | glazed carrots, rice pilaf |
| `sauce` | Finished condiment added at serve time | tzatziki, teriyaki, toum |

### `meal_type`

When you'd typically serve it.

| Value |
|-------|
| `breakfast` |
| `brunch` |
| `lunch` |
| `dinner` |
| `snack` |
| `dessert` |
| `anytime` |

Use `anytime` for sauces, preserves, components, and technique guides.

### `meal_role`

Optional. Use when it clarifies how the dish fits a meal.

| Value |
|-------|
| `one_dish_meal` |
| `side_dish` |

Do not use `appetizer` — legacy appetizer categories map to `dish_type: [side]`.

---

## `X-tags`

### `cuisine`

Open list — pick the closest match. Examples:

| Value | Value | Value |
|-------|-------|-------|
| `american` | `italian` | `thai` |
| `indian` | `mexican` | `chinese` |
| `japanese` | `korean` | `french` |
| `german` | `mediterranean` | `middle_eastern` |
| `greek` | `cajun` | `scandinavian` |
| `seafood` | | |

Use a single base cuisine when possible (`japanese`, `italian`, `american`, `asian`). Do **not** use `-inspired` suffixes — map `Japanese-Inspired` → `japanese`. Legacy flat `X-tags` entries like `Japanese` or `Mexican-inspired` also belong here. Use `seafood` for fish- and shellfish-forward mains (legacy `X-category: seafood`).

### `dietary`

Restrictions the recipe satisfies **as written**.

| Value | Notes |
|-------|-------|
| `vegetarian` | No meat/fish |
| `vegan` | No animal products |
| `pescatarian` | Fish OK, no meat |
| `gluten_free` | As written |
| `dairy_free` | As written |
| `egg_free` | Optional |
| `nut_free` | Optional |
| `whole30` | |
| `low_sugar` | Especially preserves |

**Adaptables** — use only when the recipe can be modified, not as a primary dietary tag unless intentional:

| Value |
|-------|
| `vegetarian_adaptable` |
| `vegan_adaptable` |
| `gluten_free_adaptable` |

### `method`

Primary cooking technique. Pick 1–2.

| Value |
|-------|
| `oven` |
| `stovetop` |
| `slow_cooker` |
| `instant_pot` |
| `grill` |
| `no_cook` |
| `air_fryer` |
| `deep_fry` |
| `preserve` |
| `blender` |

### `context`

| Value |
|-------|
| `weeknight` |
| `quick` |
| `comfort_food` |
| `holiday` |
| `entertaining` |
| `freezer-friendly` |
| `make_ahead` |
| `meal_prep` |
| `leftovers_friendly` |

### `season`

| Value |
|-------|
| `spring` |
| `summer` |
| `fall` |
| `winter` |

### `primary_ingredient`

Open list — main ingredients worth filtering on. Examples:

`potatoes`, `chickpeas`, `chicken`, `beef`, `pork`, `fish`, `beans`, `tofu`, `squash`, `pasta`, `rice`, `mushrooms`, `eggs`, `turkey`, `lamb`, `shrimp`, `salmon`

### `flavor_profile`

Suggested values (open list):

| Value |
|-------|
| `savory` |
| `hearty` |
| `spicy` |
| `sweet` |
| `tangy` |
| `creamy` |
| `smoky` |
| `fresh` |

---

## Example: Bratkartoffeln

```yaml
recipe_uuid: wc-kitchen.bratkartoffeln
recipe_name: Bratkartoffeln

X-categories:
  dish_type:
    - main
  meal_type:
    - dinner

X-tags:
  cuisine:
    - german
  method:
    - stovetop
  primary_ingredient:
    - potatoes
    - bacon
  flavor_profile:
    - savory
    - hearty
  context:
    - leftovers_friendly

X-total_time: 60 minutes
X-active_time: 60 minutes
X-nutrition:
  calories: 615
  fiber: 9 g
X-original-source: ../originals/bratkartoffeln-20260523.jpg
X-source-verification:
  status: verified
  notes:
    - Custom recipe card format; no external source URL visible
```

---

## Metadata checklist

### Required for normal recipes

| Field | Rule |
|-------|------|
| `X-categories` | At minimum `dish_type` and `meal_type` once migration is complete |
| `X-tags` | At minimum `method` when applicable; add `dietary` when relevant |
| `X-source-verification` | Always present; `status` is one of: `verified`, `needs-review`, `needs-manual-review` |

**Until migration is complete**, legacy `X-category` and flat `X-tags` satisfy the audit instead of structured fields.

### Recommended

| Field | Rule |
|-------|------|
| `source_authors` | When known (from print or site) |
| `X-prep_time` / `X-cook_time` / `X-active_time` / `X-total_time` | When visible on source |
| `description` | One short sentence (optional; helps index/HTML) |
| `X-nutrition` | When visible on source |

### Other extension fields

| Field | Format |
|-------|--------|
| `source_url` | Full recipe page URL (not a site homepage) |
| `X-original-source` | Relative path to file in `originals/` |
| `X-flags` | `[index-page-not-a-recipe]` for binder index entries |
| `notes` | Recipe tips, variations, and handwritten transcription notes (not source verification) |
| `X-sub-recipes` | Nested recipes in one file (see beef brisket) |

### `source_url` rules

- **Good:** `https://www.allrecipes.com/recipe/12345/...`
- **Bad:** `https://www.allrecipes.com` (homepage only — fix URL or note in verification)
- **Custom cards:** omit `source_url`; use `X-original-source` only

### Verification status

| Status | When |
|--------|------|
| `verified` | YAML matches source image/print |
| `needs-review` | Extracted or not yet checked |
| `needs-manual-review` | Incomplete source (partial photo, scaling table, missing quantities) |

Optional: `last_checked: 2026-05-23` inside `X-source-verification`.

---

## Special entry types

### Binder index photos (not meals)

```yaml
X-flags: [index-page-not-a-recipe]
X-categories:
  dish_type:
    - reference
```

No `ingredients` or `steps` required. Do not use for shopping lists.

### In-progress drafts (`recipes/in-progress/`)

Same filename and `recipe_uuid` as published recipes. Path-only differences:

| Field | Top-level `recipes/` | `recipes/in-progress/` |
|-------|----------------------|-------------------------|
| `X-original-source` | `../originals/...` | `../../originals/...` |

When promoting a draft, move the file to `recipes/` and revert the path.

### Other patterns

| Type | Extra metadata |
|------|----------------|
| Scaling table (jam) | `dish_type: [preserve]`; note scaling reference in `X-source-verification` |
| Incomplete extract | `needs-manual-review` + note to verify against `source_url` |
| Sub-recipes in one file | `X-sub-recipes` (see beef brisket); tag parent e.g. `includes-latkes` |

---

## Batch fix priority

After bulk migration or extract:

1. Bare `source_url` → full recipe URLs
2. `author` → `source_authors`
3. Migrate legacy `X-category` / flat `X-tags` / `X-dietary` → structured `X-categories` / `X-tags`
4. Replace `X-flags: []` with full `X-source-verification` block
5. Mark index pages as `dish_type: [reference]`
6. Drop flat `X-tags` that restate `recipe_name` — `python scripts/clean_title_tags.py` (use `--dry-run` first)
7. Migrate legacy metadata to structured fields — `python scripts/batch_fix_metadata.py [directory]` (use `--dry-run` first; sample set in `recipes/sample/`)

The batch fix script also:

- Removes `X-rating` and `X-rating_count`
- Drops `X-freezer_friendly: false`; converts `true` → `X-tags.context: [freezer-friendly]`
- Infers `X-tags.method` from recipe text (`slow cooker` / `crockpot` → `slow_cooker`; `instant pot` → `instant_pot`; `oven` or an oven temperature → `oven`, excluding Dutch oven)
- Infers `X-tags.dietary` from recipe text (`vegetarian`, `vegan`; skips adaptation-only phrasing such as “to make vegetarian” or `vegetarian_adaptable` recipes unless name/slug/description says so; `vegan` also adds `vegetarian`)
- Moves `X-tags.planning` values (`make_ahead`, `meal_prep`, `leftovers_friendly`, `freezer-friendly`) → `X-tags.context`
- Moves `X-tips`, `X-notes`, and `X-handwritten-*` fields into ORF `notes`
- Infers missing `X-categories` from `X-course`, recipe name, and `SPECIAL_DISH_TYPE`
- Drops redundant `X-course` when categories are already set
- Consolidates duplicate fields: `X-author` / `X-source-author` → `source_authors`; `X-equipment` → `equipment`; `X-method` → `X-tags.method`; `X-source-description` → `description`; `X-calories` → `X-nutrition.calories`; `X-hands_on_time` → `X-active_time` (when missing)
- Drops TV/provenance duplicates: `X-show`, `X-episode`, `X-publisher`, `X-copyright`, `X-published`, `X-source-publication`, `X-source-updated`, `X-attribution`
- Normalizes cuisine tags (drops `-inspired` suffixes)
- Moves all `X-*` fields to the end of each YAML file

---

## Audit reference

`recipe audit-metadata` reports these issue codes:

`bare-source-url`, `missing-category`, `missing-tags`, `missing-verification`, `legacy-author`, `category-format`, `empty-flags-only`, `missing-provenance`, `reference-category`, `dish-type-count` (guidance only — prefer 1–2 `X-categories.dish_type` values)

Script equivalent: `python scripts/audit_metadata.py`
