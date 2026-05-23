# Shopping list generation

Use the recipe collection YAML files to build a shopping list.

## Discovery

1. Read [`recipes/index.yaml`](../recipes/index.yaml) for the full library (names, tags, links).
2. Load individual recipes from [`recipes/`](../recipes/) using the `links.yaml` path in the index.

## Ingredient structure (strict ORF)

Each ingredient is a single-key dict:

```yaml
ingredients:
  - Yukon gold potatoes:
      amounts:
        - amount: 3
          unit: lb
```

Use the dict **key** as the ingredient name and `amounts[0]` for quantity.

## Rules

- Combine ingredients across recipes when **name and unit** match (case-insensitive name).
- Sum numeric amounts; keep fractions when exact.
- When units differ or amounts are ambiguous ("to taste"), list separately.
- Include `processing` notes in the display name when relevant (e.g. "onions, chopped").
- Prefer the CLI when available: `recipe shop wc-kitchen.a wc-kitchen.b`

## Output format

Markdown bullet list grouped by category if `X-category` is set, otherwise alphabetical:

```markdown
# Shopping list

- 3 lb yukon gold potatoes
- 1/4 cup salt
```

Flag conflicts explicitly rather than silently merging.
