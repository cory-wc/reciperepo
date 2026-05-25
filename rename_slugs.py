#!/usr/bin/env python3
"""
rename_slugs.py — Normalize recipe YAML filenames and recipe_uuid values
to kebab-case slugs derived from the recipe_name field.

Usage:
    python rename_slugs.py           # dry run (shows proposed changes)
    python rename_slugs.py --apply   # apply renames

Rules (mirrors notes.md):
  - Kebab-case from title
  - Parenthetical content stripped  e.g. "(Instant Pot)" removed
  - & → and
  - Apostrophes removed
  - Non-alphanumeric chars replaced with hyphens
  - Consecutive hyphens collapsed
  - Namespace prefix preserved: wc-kitchen.{slug}
"""

import re
import sys
from pathlib import Path

import yaml

RECIPES_DIR = Path(__file__).parent / "recipes"
NAMESPACE = "wc-kitchen"


def name_to_slug(name: str) -> str:
    """Convert a recipe_name to a kebab-case slug."""
    # Strip parenthetical content
    name = re.sub(r"\(.*?\)", "", name)
    # Replace & with "and"
    name = name.replace("&", "and")
    # Remove apostrophes / curly quotes
    name = re.sub(r"[''\"']", "", name)
    # Lowercase
    name = name.lower()
    # Replace any non-alphanumeric char with a hyphen
    name = re.sub(r"[^a-z0-9]+", "-", name)
    # Collapse and strip edge hyphens
    name = name.strip("-")
    return name


def main(apply: bool = False) -> None:
    yamls = sorted(p for p in RECIPES_DIR.glob("*.yaml") if p.name != "index.yaml")

    renames: list[tuple[Path, Path, str, str]] = []  # (old_path, new_path, old_uuid, new_uuid)
    already_ok: list[str] = []
    errors: list[str] = []

    for path in yamls:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"  PARSE ERROR {path.name}: {e}")
            continue

        recipe_name = data.get("recipe_name", "")
        if not recipe_name:
            errors.append(f"  NO recipe_name in {path.name}")
            continue

        slug = name_to_slug(recipe_name)
        new_uuid = f"{NAMESPACE}.{slug}"
        new_filename = f"{new_uuid}.yaml"
        new_path = RECIPES_DIR / new_filename

        if path.name == new_filename:
            already_ok.append(path.name)
        else:
            renames.append((path, new_path, data.get("recipe_uuid", ""), new_uuid))

    # Report
    print(f"\n{'DRY RUN' if not apply else 'APPLYING'} — {len(yamls)} recipes scanned\n")

    if already_ok:
        print(f"  ✓ {len(already_ok)} already correctly named")

    if renames:
        print(f"\n  {'Would rename' if not apply else 'Renaming'} {len(renames)}:")
        for old_path, new_path, old_uuid, new_uuid in renames:
            print(f"    {old_path.name}")
            print(f"      → {new_path.name}")
            if old_uuid != new_uuid:
                print(f"      recipe_uuid: {old_uuid!r} → {new_uuid!r}")

        if apply:
            for old_path, new_path, old_uuid, new_uuid in renames:
                text = old_path.read_text(encoding="utf-8")
                # Update recipe_uuid in file
                text = text.replace(
                    f"recipe_uuid: {old_uuid}",
                    f"recipe_uuid: {new_uuid}",
                    1,
                )
                new_path.write_text(text, encoding="utf-8")
                old_path.unlink()
                print(f"  Renamed: {old_path.name} → {new_path.name}")
    else:
        print("  ✓ No renames needed")

    if errors:
        print(f"\n  ⚠ {len(errors)} errors:")
        for e in errors:
            print(e)

    if not apply and renames:
        print("\nRun with --apply to execute renames.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
