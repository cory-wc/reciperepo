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

## Metadata checklist

### Required for normal recipes

| Field | Rule |
|-------|------|
| `X-category` | List, lowercase kebab-case: `[dinner]`, `[breakfast]`, `[side]`, `[dessert]`, `[sauce]`, `[soup]`, `[preserve]` |
| `X-tags` | List: cuisine, method, dish name (`korean`, `instant-pot`, `sloppy-joes`) |
| `X-source-verification` | Always present; `status` is one of: `verified`, `needs-review`, `needs-manual-review` |

### Recommended

| Field | Rule |
|-------|------|
| `X-dietary` | Restrictions only: `vegan`, `gluten-free`, `dairy-free` (lowercase) |
| `source_authors` | When known (from print or site) |
| `X-prep_time` / `X-cook_time` / `X-total_time` | When visible on source |
| `description` | One short sentence (optional; helps index/HTML) |

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
X-category: [reference]
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
| Scaling table (jam) | `X-category: [preserve, reference]`; tag `scaling-table` |
| Incomplete extract | `needs-manual-review` + note to verify against `source_url` |
| Sub-recipes in one file | `X-sub-recipes` (see beef brisket); tag parent e.g. `includes-latkes` |

---

## Batch fix priority

After bulk migration or extract:

1. Bare `source_url` → full recipe URLs
2. `author` → `source_authors`
3. Add `X-category` / `X-tags` on sparse custom-card files
4. Replace `X-flags: []` with full `X-source-verification` block
5. Normalize `X-category` to lowercase lists
6. Mark index pages as `reference`

---

## Audit reference

`recipe audit-metadata` reports these issue codes:

`bare-source-url`, `missing-category`, `missing-tags`, `missing-verification`, `legacy-author`, `category-format`, `empty-flags-only`, `missing-provenance`, `reference-category`

Script equivalent: `python scripts/audit_metadata.py`
