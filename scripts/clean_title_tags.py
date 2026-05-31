#!/usr/bin/env python3
"""Remove flat X-tags that restate recipe_name (see notes.md migration rules)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
RECIPES = REPO / "recipes"

STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "with",
    "for",
    "of",
    "in",
    "on",
    "i",
    "ii",
    "iii",
    "recipe",
    "best",
    "easy",
    "how",
    "to",
    "make",
    "your",
    "my",
    "homemade",
    "actually",
    "delicious",
    "ultimate",
    "perfect",
    "beginners",
    "guide",
    "minute",
    "minutes",
    "hour",
    "hours",
    "dairy",
    "free",
    "clone",
    "copycat",
}

FACET_TAGS = {
    "instant pot",
    "pressure cooker",
    "slow cooker",
    "slow cooker option",
    "oven",
    "stovetop",
    "grilled",
    "roasted",
    "baked",
    "one pot",
    "one-pot",
    "one-pan",
    "one pan",
    "skillet",
    "no-cook",
    "no cook",
    "pan-fried",
    "pan fried",
    "air fryer",
    "canning",
    "preserving",
    "blender",
    "emulsion",
    "blackened",
    "smashed",
    "crispy",
    "creamy",
    "glazed",
    "vegetarian",
    "vegan",
    "pescatarian",
    "gluten-free",
    "gluten free",
    "dairy-free",
    "dairy free",
    "whole30",
    "whole 30",
    "vegetarian-adaptable",
    "vegetarian adaptable",
    "low-fat",
    "low fat",
    "low-sugar",
    "low sugar",
    "no-sugar",
    "no sugar",
    "healthy",
    "american",
    "italian",
    "italian-american",
    "thai",
    "mexican",
    "mexican-inspired",
    "mexican inspired",
    "korean",
    "japanese",
    "japanese-inspired",
    "japanese inspired",
    "french",
    "greek",
    "lebanese",
    "middle eastern",
    "tuscan",
    "cajun",
    "asian",
    "asian-inspired",
    "asian inspired",
    "indian",
    "mediterranean",
    "western",
    "scandinavian",
    "swedish",
    "weeknight",
    "weeknight dinner",
    "quick",
    "easy",
    "comfort food",
    "holiday",
    "make-ahead",
    "make ahead",
    "meal prep",
    "freezer friendly",
    "freezer-friendly",
    "fall",
    "summer",
    "spring",
    "winter",
    "thanksgiving",
    "christmas",
    "side dish",
    "dessert",
    "breakfast",
    "brunch",
    "cold",
    "spicy",
    "baking",
    "preserving",
    "condiment",
    "sauce",
    "marinade",
    "dressing",
    "pastry",
    "whole grain",
    "budget-friendly",
    "budget friendly",
    "21 day fix",
    "dorm room dinner",
    "pantry staples",
    "stir fry",
    "seafood",
    "fish",
    "quick",
}


def norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def sig_words(text: str) -> list[str]:
    return [w for w in norm(text).split() if w not in STOP and len(w) > 1]


def slug_text(recipe_id: str) -> str:
    slug = recipe_id.split(".", 1)[-1]
    return norm(slug.replace("-", " "))


def dish_phrases(recipe_name: str, recipe_id: str) -> set[str]:
    phrases: set[str] = set()
    for source in (slug_text(recipe_id), norm(recipe_name)):
        words = sig_words(source)
        if not words:
            continue
        phrases.add(" ".join(words))
        for n in (2, 3, 4):
            for i in range(len(words) - n + 1):
                phrases.add(" ".join(words[i : i + n]))
    return {p for p in phrases if len(p) > 2}


def is_facet_tag(tag: str) -> bool:
    return norm(tag) in FACET_TAGS


def is_title_restate(tag: str, recipe_name: str, recipe_id: str) -> bool:
    if is_facet_tag(tag):
        return False

    t = norm(tag)
    if not t:
        return True

    phrases = dish_phrases(recipe_name, recipe_id)
    if t in phrases:
        return True

    for phrase in phrases:
        if len(phrase.split()) >= 2 and phrase in t:
            return True

    if t.endswith(" recipe"):
        core = t[: -len(" recipe")].strip()
        if core in phrases or core in norm(recipe_name) or core in slug_text(recipe_id):
            return True

    tag_words = sig_words(tag)
    slug_words = sig_words(slug_text(recipe_id))
    name_words = sig_words(recipe_name)
    if len(tag_words) == 1:
        w = tag_words[0]
        if w in slug_words and w in name_words and len(slug_words) <= 4:
            return True
        # singular/plural match for short slugs (cookie/cookies)
        for sw in slug_words:
            if w == sw or w == sw.rstrip("s") or w + "s" == sw:
                if w in name_words or sw in name_words:
                    return True

    return False


def _patch_x_tags_block(lines: list[str], kept: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("X-tags:"):
            out.append(line)
            i += 1
            continue

        if not kept:
            i += 1
            while i < len(lines) and lines[i].startswith("- "):
                i += 1
            continue

        out.append("X-tags:")
        for tag in kept:
            out.append(f"- {tag}")
        i += 1
        while i < len(lines) and lines[i].startswith("- "):
            i += 1
    return out


def clean_file(path: Path, *, dry_run: bool) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []

    tags = data.get("X-tags")
    if not tags:
        return []

    if isinstance(tags, str):
        tags = [tags]

    recipe_id = data.get("recipe_uuid", path.stem)
    recipe_name = data.get("recipe_name", recipe_id)

    kept: list[str] = []
    removed: list[str] = []
    for tag in tags:
        if is_title_restate(str(tag), str(recipe_name), str(recipe_id)):
            removed.append(str(tag))
        else:
            kept.append(str(tag))

    if not removed:
        return []

    if not dry_run:
        original = path.read_text(encoding="utf-8").splitlines(keepends=True)
        plain_lines = [ln.rstrip("\n") for ln in original]
        patched = _patch_x_tags_block(plain_lines, kept)
        path.write_text("\n".join(patched) + ("\n" if original else ""), encoding="utf-8")

    return [f"{recipe_id}: dropped {removed!r}" + (f", kept {kept!r}" if kept else ", removed X-tags")]


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    lines: list[str] = []
    for path in sorted(RECIPES.glob("wc-kitchen.*.yaml")):
        lines.extend(clean_file(path, dry_run=dry_run))

    for line in lines:
        print(line)
    print(f"\n{'Would update' if dry_run else 'Updated'} {len(lines)} recipe(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
