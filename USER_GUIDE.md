# Recipe collection — user guide

Non-technical walkthrough for day-to-day use. For CLI details, CI, and repo layout see [README.md](README.md). For YAML rules see [notes.md](notes.md). Doc roles: [docs/documentation.md](docs/documentation.md).

Your recipes live in a Git repo. Each recipe usually has:

- **Source files** (`originals/`) — photos, PDFs, or prints (canonical truth)
- **Recipe data** (`recipes/`) — standardized YAML
- **Printable card** (`pdfs/`) — for your binder
- **Web page** (`site/`) — browse on phone or laptop (GitHub Pages)

Details for naming and metadata: [`notes.md`](notes.md).

---

## One-time setup

1. Open the project: `Documents/Recipes/reciperepo`
2. Activate the tool: `source .venv/bin/activate` (after `pip install -e .` once)
3. Optional: `cp .env.example .env` — only needed for automated extract from photos
4. Optional: `playwright install chromium` — for generating PDFs
5. Pull from GitHub when switching computers

---

## Recipe id and filenames

- Format: `wc-kitchen.short-name` (lowercase, hyphens)
- File: `recipes/wc-kitchen.short-name.yaml`
- Same value inside: `recipe_uuid: wc-kitchen.short-name`

---

## Add a recipe from a website

1. Copy the full recipe page URL (not just the site homepage)
2. Run:

   `recipe extract wc-kitchen.my-recipe --url "https://example.com/full/recipe/path"`

3. Open the YAML file; fix amounts and steps
4. Set `X-source-verification.status` to `reviewed` when checked
5. Publish (below)

If you also saved a print or screenshot, keep `X-original-source` pointing at the file in `originals/`.

---

## Add a recipe from a photo or PDF

1. Put source file(s) in `originals/` (keep all related photos)
2. Run:

   `recipe extract wc-kitchen.my-recipe --source originals/your-photo.jpg`

   Requires API key in `.env` (see README). Or transcribe in Cursor using `prompts/extract-orf.md` and save YAML by hand.

3. Review the YAML against the image
4. Publish (below)

---

## Bulk migration (many cookbook photos)

- Many recipes may already have YAML on the `migration` branch
- Run **`recipe audit-metadata`** to see what still needs tags, categories, full URLs, or verification
- Fix issues using the checklist in [`notes.md`](notes.md)
- Four YAML files may show `parse-error` in the audit — fix those files manually first

---

## Publish a recipe (after YAML is correct)

Run in order:

1. `recipe validate wc-kitchen.my-recipe`
2. `recipe render wc-kitchen.my-recipe` — web page in `site/`
3. `recipe pdf wc-kitchen.my-recipe` — printable PDF in `pdfs/`
4. `recipe index` — updates library list (YAML + web index + binder TOC PDF)

**All recipes:** use `--all` on render and pdf, then `recipe index`.

---

## Metadata quality

After extract or editing, run:

`recipe audit-metadata`

Common fixes (see [`notes.md`](notes.md)):

- `X-category: [dinner]` — use a **list**, lowercase (`dinner`, `side`, `dessert`, …)
- `X-tags:` — cuisine, method, dish name
- `X-source-verification` — `verified`, `needs-review`, or `needs-manual-review`
- `source_url` — full recipe link, not `https://www.allrecipes.com` alone
- `source_authors:` — use this instead of `author:`

**Binder index photos** (not meals): `X-flags: [index-page-not-a-recipe]` and `X-category: [reference]`

---

## Use your recipes

| Goal | What to use |
|------|-------------|
| Cook from printed cards | `pdfs/` (put `index.pdf` at the front of the binder) |
| Browse on phone/computer | GitHub Pages — home page is the recipe list |
| Find a recipe locally | Open `site/index.html` in a browser |
| Shopping list | `recipe shop wc-kitchen.a wc-kitchen.b` |
| What still needs work | `recipe status` and `recipe audit-metadata` |

The index is built from YAML but **links to HTML and PDF**, not raw YAML files.

---

## Review status (in each recipe YAML)

```yaml
X-source-verification:
  status: needs-review    # change to verified when checked
  notes: []
```

Compare YAML to files in `originals/` before marking `verified`.

---

## Save and sync (Git)

1. Commit: `recipes/`, `pdfs/`, `site/`, and new files in `originals/` if any
2. Push to GitHub
3. On another device: pull, then render/pdf/index if you changed YAML

---

## Troubleshooting

| Problem | Try |
|---------|-----|
| Validate fails | Read error; ingredients must use dict keys (`- sugar:`), not `ingredient:` |
| Many metadata warnings | `recipe audit-metadata` — follow [`notes.md`](notes.md) |
| PDF missing or old | `recipe pdf` then `recipe index` |
| Web page missing | `recipe render` then `recipe index` |
| Extract fails | Check `.env` API key, or transcribe YAML manually |
| Overall health | `recipe status` |

---

## What you usually skip

- Editing PDF or HTML by hand (generated from YAML)
- Listing every photo in YAML (keep files in `originals/`; one `X-original-source` is enough)
- Perfect metadata on every recipe before printing — fix in batches using `recipe audit-metadata`
