# Recipe collection — user guide

Your recipes live in a folder on your computer and sync via GitHub. Each recipe has:

- **Source files** (`originals/`) — photos, PDFs, or saved web pages (the truth)
- **Recipe data** (`recipes/`) — standardized YAML
- **Printable card** (`pdfs/`) — for your binder
- **Web page** (`site/`) — for phone or laptop (via GitHub Pages)

---

## Before you start (one-time)

1. Open the project folder: `Documents/Recipes/reciperepo`
2. Activate the tool environment (your setup already includes this)
3. Optional: pull the latest from GitHub if you use another computer

---

## Add a recipe from a website

1. Copy the recipe page URL
2. Run extract (replace the id and URL):

   `recipe extract wc-kitchen.my-recipe --url "https://example.com/recipe"`

3. Open `recipes/wc-kitchen.my-recipe.yaml` and check amounts and steps
4. Set verification to reviewed when you’re happy (see **Review status** below)
5. Build outputs (see **Publish a recipe**)

---

## Add a recipe from a photo or PDF

1. Put the file in `originals/` (keep all related photos)
2. Run extract (replace id and filename):

   `recipe extract wc-kitchen.my-recipe --source originals/your-photo.jpg`

3. Review and edit the YAML file
4. Build outputs

**Tip:** Recipe id format is `wc-kitchen.short-name` (lowercase, hyphens). The YAML filename matches: `wc-kitchen.short-name.yaml`.

---

## Publish a recipe (after YAML is correct)

Run these in order:

1. `recipe validate wc-kitchen.my-recipe` — checks the file
2. `recipe render wc-kitchen.my-recipe` — updates web page
3. `recipe pdf wc-kitchen.my-recipe` — updates printable PDF
4. `recipe index` — updates the library list

**All recipes at once:** use `--all` instead of a single id on render and pdf, then run `recipe index`.

---

## Use your recipes

| Goal | What to use |
|------|-------------|
| Cook from a printed card | Open `pdfs/` and print (or use your binder) |
| Browse on phone/computer | GitHub Pages site (home = recipe list) |
| Find a recipe quickly | Open `site/index.html` locally, or the live site |
| Shopping list for several meals | `recipe shop wc-kitchen.a wc-kitchen.b` |

---

## Recipe list (index)

- **On the web:** `site/index.html` — click a name to open that recipe
- **In the binder:** print `pdfs/index.pdf` as a table of contents
- **For tools/AI:** `recipes/index.yaml` lists every recipe with links to HTML and PDF

Regenerate after adding recipes: `recipe index`

---

## Review status

In each recipe YAML, after extraction:

```yaml
X-source-verification:
  status: needs-review    # change to reviewed when checked against originals
  notes: []
```

Always compare YAML to the source in `originals/` before marking reviewed.

---

## Naming rules

- **Id / filename:** `wc-kitchen.banana-bread`
- **Title inside file:** `recipe_name: Banana Bread`
- **Same id in:** `recipe_uuid: wc-kitchen.banana-bread`
- **Web recipes:** use `source_url` in YAML (not a file path)
- **Photos/PDFs:** use `X-original-source` pointing at a file in `originals/`

---

## Save and share (Git)

1. Commit your changes in the repo (originals, recipes, pdfs, site)
2. Push to GitHub
3. On another device: pull, then open or print as usual

---

## If something looks wrong

| Problem | Try |
|---------|-----|
| Validate fails | Read the error; fix YAML structure (ingredient names as keys, not `ingredient:`) |
| PDF missing or old | `recipe pdf` then `recipe index` |
| Web page missing | `recipe render` then `recipe index` |
| Index warns about stale files | Run render and pdf first, then index |
| Check overall status | `recipe status` |

---

## What not to worry about

- You don’t edit PDF or HTML by hand — they are generated from YAML
- You don’t need to list every photo in YAML — keep files in `originals/`; one primary `X-original-source` is enough
- Adding 1–2 recipes a month is normal; bulk migration can be done gradually
