# reciperepo

Personal recipe collection in **Open Recipe Format (ORF)** YAML: sources in `originals/`, printable PDFs for a binder, HTML on GitHub Pages, LLM-friendly structure for shopping lists.

**User guide:** [USER_GUIDE.md](USER_GUIDE.md) (non-technical, step-by-step).

## Quick start

```bash
cd ~/Documents/Recipes/reciperepo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
cp .env.example .env   # optional: for recipe extract (vision/LLM)
```

## Workflow

```bash
# Validate ORF YAML
recipe validate wc-kitchen.bratkartoffeln
recipe validate --all

# Render cloud HTML → site/
recipe render wc-kitchen.bratkartoffeln
recipe render --all

# Printable PDF → pdfs/
recipe pdf wc-kitchen.bratkartoffeln
recipe pdf --all

# Index (metadata from YAML, links to HTML/PDF)
recipe index

# Shopping list
recipe shop wc-kitchen.bratkartoffeln

# Status dashboard
recipe status

# Metadata gaps (category, bare URL, verification)
recipe audit-metadata
```

## Extract (migration)

```bash
recipe extract wc-kitchen.new-dish --url "https://example.com/recipe"
recipe extract wc-kitchen.new-dish --source originals/scan.jpg
recipe extract --pending   # bulk: unreferenced files in originals/
```

Requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env` for image/text structuring.

## Layout

| Path | Purpose |
|------|---------|
| `recipes/` | Strict ORF YAML (+ generated `index.yaml`) |
| `originals/` | Canonical sources (photos, PDFs, text) |
| `pdfs/` | Letter-size binder PDFs + `index.pdf` |
| `site/` | GitHub Pages HTML + `index.html` |
| `prompts/` | Extraction and shopping-list instructions |

## Conventions

See [`notes.md`](notes.md): namespace `wc-kitchen.{slug}`, dict-key ingredients, `source_url` for web recipes, `X-original-source` for files.

## GitHub Pages

CI builds `site/` on push to `main`. Enable Pages: **Settings → Pages → GitHub Actions**.
