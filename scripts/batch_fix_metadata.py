#!/usr/bin/env python3
"""Migrate legacy recipe metadata to structured X-categories / X-tags (see notes.md)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]

# Import title-tag filter from sibling script
sys.path.insert(0, str(REPO / "scripts"))
from clean_title_tags import is_title_restate  # noqa: E402

SPECIAL_DISH_TYPE: dict[str, list[str]] = {
    "wc-kitchen.instant-pot-black-beans": ["component", "side"],
    "wc-kitchen.how-to-make-instant-pot-farro": ["component", "side"],
    "wc-kitchen.pasta-e-piselli": ["pasta"],
    "wc-kitchen.shepherds-pie": ["one_dish"],
    "wc-kitchen.bratkartoffeln": ["main"],
    "wc-kitchen.vegetarian-burrito-bowls": ["bowl"],
    "wc-kitchen.thai-peanut-sweet-potato-buddha-bowl": ["bowl"],
    "wc-kitchen.chana-masala": ["main"],
    "wc-kitchen.chili-recipe": ["soup"],
    "wc-kitchen.binder-index": ["reference"],
    "wc-kitchen.your-strawberry-jam-recipe": ["preserve"],
    "wc-kitchen.tzatziki": ["sauce"],
    "wc-kitchen.fluffy-almond-flour-pancakes": ["bread"],
    "wc-kitchen.waffles-i": ["bread"],
    "wc-kitchen.creamy-tomato-soup": ["soup"],
    "wc-kitchen.spaghetti-carbonara": ["pasta"],
    "wc-kitchen.15-minute-miso-soup-with-greens-and-tofu": ["soup"],
}

# Tags to apply when legacy metadata was sparse (manual curation per notes.md rules).
INFERRED_TAGS: dict[str, dict[str, list[str]]] = {
    "wc-kitchen.chana-masala": {
        "cuisine": ["indian"],
        "dietary": ["vegetarian"],
        "method": ["stovetop"],
    },
    "wc-kitchen.bratkartoffeln": {
        "cuisine": ["german"],
        "method": ["stovetop"],
        "primary_ingredient": ["potatoes", "bacon"],
    },
    "wc-kitchen.shepherds-pie": {
        "method": ["oven"],
        "planning": ["leftovers_friendly"],
        "primary_ingredient": ["potatoes"],
        "flavor_profile": ["savory", "hearty"],
    },
    "wc-kitchen.spaghetti-carbonara": {
        "cuisine": ["italian"],
        "method": ["stovetop"],
    },
    "wc-kitchen.creamy-tomato-soup": {
        "method": ["stovetop"],
        "flavor_profile": ["creamy"],
    },
    "wc-kitchen.the-best-swedish-meatballs-recipe": {
        "cuisine": ["scandinavian"],
        "method": ["stovetop"],
    },
}

# Top-level fields to drop during cleanup.
DROP_FIELDS = frozenset(
    {
        "X-rating",
        "X-rating_count",
        "X-freezer-friendly",
        "X-freezer_friendly",
        "X-tips",
        "X-handwritten-notes",
        "X-handwritten-alt-ingredients",
        "X-handwritten-optional-fillings",
    }
)

# Non-extension fields first; all `X-*` keys moved to the end.
CORE_KEY_ORDER = [
    "recipe_uuid",
    "recipe_name",
    "description",
    "source_url",
    "source_authors",
    "yields",
    "ingredients",
    "steps",
    "notes",
    "equipment",
]

X_KEY_ORDER = [
    "X-categories",
    "X-tags",
    "X-source-verification",
    "X-original-source",
    "X-prep_time",
    "X-cook_time",
    "X-active_time",
    "X-total_time",
    "X-cooling_time",
    "X-nutrition",
    "X-storage",
    "X-method",
    "X-author",
    "X-publisher",
    "X-calories",
    "X-equipment",
    "X-sub-recipes",
    "X-flags",
]

# Unclassified flat tags to drop (not worth a taxonomy bucket).
DROP_TAGS = {
    "gravy",
    "recipe",
    "side dish",
    "side",
    "dessert",
    "food network kitchen",
}

DISH_TYPE_FROM_LEGACY: dict[str, str] = {
    "soup": "soup",
    "salad": "salad",
    "pasta": "pasta",
    "main": "main",
    "main dish": "main",
    "main course": "main",
    "main dishes": "main",
    "mains": "main",
    "entree": "main",
    "entrée": "main",
    "side dish": "side",
    "side": "side",
    "sides": "side",
    "condiment": "sauce",
    "sauces": "sauce",
    "sauce": "sauce",
    "dip": "sauce",
    "preserve": "preserve",
    "preserves": "preserve",
    "jam / preserve": "preserve",
    "dessert": "dessert",
    "cookie": "dessert",
    "quick bread": "bread",
    "muffin": "bread",
    "breakfast": "bread",
    "quiche": "breakfast_bake",
    "cocktail": "beverage",
    "seafood": "main",
    "appetizer": "side",
    "reference": "reference",
}

MEAL_TYPE_FROM_LEGACY: dict[str, str] = {
    "breakfast": "breakfast",
    "brunch": "brunch",
    "lunch": "lunch",
    "dinner": "dinner",
    "snack": "snack",
    "dessert": "dessert",
}

METHOD_TAGS: dict[str, str] = {
    "instant pot": "instant_pot",
    "pressure cooker": "instant_pot",
    "slow cooker": "slow_cooker",
    "slow cooker option": "slow_cooker",
    "oven": "oven",
    "stovetop": "stovetop",
    "grilled": "grill",
    "grill": "grill",
    "roasted": "oven",
    "roast": "oven",
    "baked": "oven",
    "baking": "oven",
    "one pot": "stovetop",
    "one-pot": "stovetop",
    "one-pan": "oven",
    "one pan": "oven",
    "skillet": "stovetop",
    "no-cook": "no_cook",
    "no cook": "no_cook",
    "pan-fried": "stovetop",
    "pan fried": "stovetop",
    "canning": "preserve",
    "preserving": "preserve",
    "blender": "blender",
    "blackened": "stovetop",
}

CONTEXT_TAGS: dict[str, str] = {
    "weeknight": "weeknight",
    "weeknight dinner": "weeknight",
    "quick": "quick",
    "easy": "quick",
    "comfort food": "comfort_food",
    "holiday": "holiday",
    "entertaining": "entertaining",
    "freezer-friendly": "freezer-friendly",
    "freezer friendly": "freezer-friendly",
}

PLANNING_TAGS: dict[str, str] = {
    "make-ahead": "make_ahead",
    "make ahead": "make_ahead",
    "meal prep": "meal_prep",
    "leftovers friendly": "leftovers_friendly",
    "budget-friendly": "meal_prep",
    "budget friendly": "meal_prep",
}

SEASON_TAGS: dict[str, str] = {
    "spring": "spring",
    "summer": "summer",
    "fall": "fall",
    "winter": "winter",
    "christmas": "winter",
    "thanksgiving": "fall",
}

CUISINE_TAGS: dict[str, str] = {
    "american": "american",
    "italian": "italian",
    "italian-american": "italian",
    "thai": "thai",
    "mexican": "mexican",
    "mexican-inspired": "mexican",
    "mexican inspired": "mexican",
    "korean": "korean",
    "japanese": "japanese",
    "japanese-inspired": "japanese",
    "japanese inspired": "japanese",
    "french": "french",
    "greek": "greek",
    "lebanese": "middle_eastern",
    "middle eastern": "middle_eastern",
    "tuscan": "italian",
    "cajun": "cajun",
    "asian": "asian",
    "asian-inspired": "asian",
    "asian inspired": "asian",
    "indian": "indian",
    "mediterranean": "mediterranean",
    "western": "american",
    "scandinavian": "scandinavian",
    "swedish": "scandinavian",
    "german": "german",
    "seafood": "seafood",
}

DIETARY_TAGS: dict[str, str] = {
    "vegetarian": "vegetarian",
    "vegan": "vegan",
    "pescatarian": "pescatarian",
    "gluten-free": "gluten_free",
    "gluten free": "gluten_free",
    "dairy-free": "dairy_free",
    "dairy free": "dairy_free",
    "whole30": "whole30",
    "whole 30": "whole30",
    "vegetarian-adaptable": "vegetarian_adaptable",
    "vegetarian adaptable": "vegetarian_adaptable",
    "gluten-free adaptable": "gluten_free_adaptable",
    "gluten free adaptable": "gluten_free_adaptable",
    "low-fat": "low_fat",
    "low fat": "low_fat",
    "low-sugar": "low_sugar",
    "low sugar": "low_sugar",
    "no-sugar": "low_sugar",
    "no sugar": "low_sugar",
    "healthy": "low_sugar",
}


def norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", " ", text)
    return " ".join(text.split())


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if "," in value:
            return [p.strip() for p in value.split(",") if p.strip()]
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _normalize_cuisine_value(value: str) -> str:
    """Cuisine tags use base names only (japanese, not japanese_inspired)."""
    v = value.replace("-", "_").lower().strip()
    if v.endswith("_inspired"):
        v = v[: -len("_inspired")]
    return v


def _is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


def _ensure_structured_tags(data: dict[str, Any]) -> dict[str, list[str]]:
    tags = data.get("X-tags")
    if isinstance(tags, dict):
        return tags
    structured, _ = _build_structured_tags(data, _legacy_categories(data))
    if structured:
        data["X-tags"] = structured
    elif "X-tags" in data:
        del data["X-tags"]
    return data.get("X-tags") or {}


def _normalize_cuisine_in_tags(data: dict[str, Any]) -> bool:
    tags = data.get("X-tags")
    if not isinstance(tags, dict) or "cuisine" not in tags:
        return False
    before = list(tags["cuisine"])
    tags["cuisine"] = _unique(_normalize_cuisine_value(v) for v in tags["cuisine"])
    return tags["cuisine"] != before


def _ensure_notes_list(data: dict[str, Any]) -> list[str]:
    notes = data.get("notes")
    if notes is None:
        data["notes"] = []
    elif isinstance(notes, str):
        data["notes"] = [notes] if notes.strip() else []
    elif isinstance(notes, list):
        data["notes"] = [str(n) for n in notes if str(n).strip()]
    else:
        data["notes"] = [str(notes)]
    return data["notes"]


def _append_note(data: dict[str, Any], text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    notes = _ensure_notes_list(data)
    if text in notes:
        return False
    notes.append(text)
    return True


def _append_notes(data: dict[str, Any], items: Any) -> int:
    added = 0
    for item in _as_list(items):
        if _append_note(data, item):
            added += 1
    return added


def _format_ingredient_line(entry: Any) -> str:
    if not isinstance(entry, dict):
        return str(entry)
    for name, body in entry.items():
        if not isinstance(body, dict):
            return f"{name}: {body}"
        amounts = body.get("amounts") or []
        parts: list[str] = []
        for amount in amounts:
            if isinstance(amount, dict):
                amt = amount.get("amount", "")
                unit = amount.get("unit", "")
                parts.append(f"{amt} {unit}".strip())
        line = f"{name}: {', '.join(parts) if parts else 'see source'}"
        ing_notes = body.get("notes")
        if ing_notes:
            line += f" ({ing_notes})"
        return line
    return str(entry)


def _migrate_handwritten_and_tips(data: dict[str, Any]) -> list[str]:
    """Move X-tips and X-handwritten-* fields into ORF `notes`."""
    changes: list[str] = []

    if "X-tips" in data:
        added = _append_notes(data, data.pop("X-tips"))
        if added:
            changes.append(f"X-tips → notes ({added} item(s))")

    if "X-handwritten-notes" in data:
        value = data.pop("X-handwritten-notes")
        added = _append_notes(data, value)
        if added:
            changes.append(f"X-handwritten-notes → notes ({added} item(s))")

    if "X-handwritten-alt-ingredients" in data:
        block = data.pop("X-handwritten-alt-ingredients")
        added = 0
        if isinstance(block, dict):
            if block.get("notes"):
                added += int(_append_note(data, str(block["notes"])))
            for entry in block.get("ingredients") or []:
                line = _format_ingredient_line(entry)
                added += int(_append_note(data, f"Handwritten alternate ingredient: {line}"))
        else:
            added += int(_append_note(data, str(block)))
        if added:
            changes.append(f"X-handwritten-alt-ingredients → notes ({added} item(s))")

    if "X-handwritten-optional-fillings" in data:
        block = data.pop("X-handwritten-optional-fillings")
        added = 0
        if isinstance(block, dict):
            if block.get("notes"):
                added += int(_append_note(data, str(block["notes"])))
            for item in block.get("items") or []:
                added += int(_append_note(data, f"Handwritten optional filling: {item}"))
        else:
            added += int(_append_note(data, str(block)))
        if added:
            changes.append(f"X-handwritten-optional-fillings → notes ({added} item(s))")

    if "notes" in data and data["notes"] == []:
        del data["notes"]

    return changes


def _relocate_freezer_friendly(data: dict[str, Any]) -> bool:
    """Move freezer-friendly from X-tags.planning to X-tags.context."""
    tags = data.get("X-tags")
    if not isinstance(tags, dict):
        return False

    planning = tags.get("planning") or []
    if not planning:
        return False

    moved = False
    kept: list[str] = []
    for value in planning:
        normalized = value.replace("_", "-").lower()
        if normalized in {"freezer-friendly", "freezer friendly"}:
            tags.setdefault("context", [])
            if "freezer-friendly" not in tags["context"]:
                tags["context"].append("freezer-friendly")
            moved = True
        else:
            kept.append(value)

    if not moved:
        return False

    if kept:
        tags["planning"] = _unique(kept)
    elif "planning" in tags:
        del tags["planning"]

    structured = {k: v for k, v in tags.items() if v}
    if structured:
        data["X-tags"] = structured
    elif "X-tags" in data:
        del data["X-tags"]
    return True


def _cleanup_dropped_fields(data: dict[str, Any]) -> list[str]:
    changes: list[str] = []

    for key in ("X-rating", "X-rating_count"):
        if key in data:
            del data[key]
            changes.append(f"removed {key}")

    for freezer_key in ("X-freezer_friendly", "X-freezer-friendly"):
        if freezer_key not in data:
            continue
        value = data.pop(freezer_key)
        if _is_truthy(value):
            tags = _ensure_structured_tags(data)
            tags.setdefault("context", [])
            if "freezer-friendly" not in tags["context"]:
                tags["context"].append("freezer-friendly")
            data["X-tags"] = tags
            changes.append(f"{freezer_key}: true → X-tags.context [freezer-friendly]")
        else:
            changes.append(f"removed {freezer_key}")

    return changes


def reorder_recipe_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Put core ORF body first, other non-X keys next, then all X-* keys at the end."""
    non_x: list[str] = []
    x_keys: list[str] = []
    for key in data:
        if key.startswith("X-"):
            x_keys.append(key)
        else:
            non_x.append(key)

    ordered: dict[str, Any] = {}
    for key in CORE_KEY_ORDER:
        if key in data:
            ordered[key] = data[key]
    for key in non_x:
        if key not in ordered:
            ordered[key] = data[key]
    for key in X_KEY_ORDER:
        if key in data:
            ordered[key] = data[key]
    for key in sorted(x_keys):
        if key not in ordered:
            ordered[key] = data[key]
    return ordered


def _dump_recipe(data: dict[str, Any]) -> str:
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _legacy_categories(data: dict[str, Any]) -> list[str]:
    return _as_list(data.get("X-category"))


def _infer_dish_and_meal_types(
    recipe_id: str, legacy_cats: list[str]
) -> tuple[list[str], list[str]]:
    if recipe_id in SPECIAL_DISH_TYPE:
        dish = SPECIAL_DISH_TYPE[recipe_id]
        meal = _infer_meal_type(recipe_id, legacy_cats, dish)
        return dish, meal

    dish_types: list[str] = []
    meal_types: list[str] = []

    for raw in legacy_cats:
        key = norm(raw)
        if key in MEAL_TYPE_FROM_LEGACY and key not in {"dessert"}:
            meal_types.append(MEAL_TYPE_FROM_LEGACY[key])
            continue
        if key == "dinner":
            meal_types.append("dinner")
            continue
        mapped = DISH_TYPE_FROM_LEGACY.get(key)
        if mapped:
            dish_types.append(mapped)
        elif key == "dessert":
            dish_types.append("dessert")
            meal_types.append("dessert")

    dish_types = _unique(dish_types)
    meal_types = _unique(meal_types)

    if not dish_types:
        dish_types = ["main"]
    if not meal_types:
        meal_types = _infer_meal_type(recipe_id, legacy_cats, dish_types)

    return dish_types[:2], meal_types[:2]


def _infer_meal_type(recipe_id: str, legacy_cats: list[str], dish_types: list[str]) -> list[str]:
    if "reference" in dish_types:
        return ["anytime"]
    if "preserve" in dish_types or "sauce" in dish_types or "component" in dish_types:
        return ["anytime"]
    if "bread" in dish_types and any("breakfast" in norm(c) for c in legacy_cats):
        return ["breakfast"]
    if "breakfast_bake" in dish_types:
        return ["breakfast"]
    if "dessert" in dish_types:
        return ["dessert"]
    if "beverage" in dish_types:
        return ["anytime"]
    if any(norm(c) in {"breakfast", "brunch"} for c in legacy_cats):
        return ["breakfast"]
    if any(norm(c) == "snack" for c in legacy_cats):
        return ["snack"]
    return ["dinner"]


def _classify_flat_tag(tag: str) -> tuple[str, str] | None:
    key = norm(tag)
    for table, bucket in (
        (METHOD_TAGS, "method"),
        (DIETARY_TAGS, "dietary"),
        (CUISINE_TAGS, "cuisine"),
        (CONTEXT_TAGS, "context"),
        (PLANNING_TAGS, "planning"),
        (SEASON_TAGS, "season"),
    ):
        if key in table:
            return bucket, table[key]
    return None


def _empty_tag_buckets() -> dict[str, list[str]]:
    return {
        "cuisine": [],
        "dietary": [],
        "method": [],
        "context": [],
        "planning": [],
        "season": [],
        "primary_ingredient": [],
        "flavor_profile": [],
    }


def _should_drop_unclassified(tag: str, data: dict[str, Any]) -> bool:
    key = norm(tag)
    if key in DROP_TAGS:
        return True
    categories = data.get("X-categories") or {}
    meal_types = {norm(m) for m in _as_list(categories.get("meal_type"))}
    if key in meal_types:
        return True
    return True  # drop all unclassified flat tags


def _collect_flat_tag_sources(data: dict[str, Any]) -> list[str]:
    existing = data.get("X-tags")
    if isinstance(existing, list):
        return [str(t) for t in existing]
    if isinstance(existing, dict):
        return []
    return []


def _merge_structured_base(data: dict[str, Any]) -> dict[str, list[str]]:
    tags = _empty_tag_buckets()
    existing = data.get("X-tags")
    if isinstance(existing, dict):
        for bucket, values in existing.items():
            if bucket in tags:
                tags[bucket].extend(_as_list(values))
    for bucket in tags:
        tags[bucket] = _unique(tags[bucket])
    return tags


def _build_structured_tags(
    data: dict[str, Any], legacy_cats: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    recipe_id = str(data.get("recipe_uuid", ""))
    recipe_name = str(data.get("recipe_name", recipe_id))
    dropped: list[str] = []

    tags = _merge_structured_base(data)

    for raw in _as_list(data.get("X-cuisine")) + _as_list(data.get("X-dietary")):
        classified = _classify_flat_tag(raw)
        if classified:
            bucket, value = classified
            tags[bucket].append(value)

    for raw in _collect_flat_tag_sources(data):
        if is_title_restate(raw, recipe_name, recipe_id):
            dropped.append(raw)
            continue
        classified = _classify_flat_tag(raw)
        if classified:
            bucket, value = classified
            tags[bucket].append(value)
            continue
        if _should_drop_unclassified(raw, data):
            dropped.append(raw)
            continue
        dropped.append(raw)

    if any(norm(c) == "seafood" for c in legacy_cats):
        tags["cuisine"].append("seafood")

    if recipe_id in INFERRED_TAGS:
        for bucket, values in INFERRED_TAGS[recipe_id].items():
            if bucket in tags:
                tags[bucket].extend(values)

    for bucket in tags:
        tags[bucket] = _unique(tags[bucket])

    if tags.get("cuisine"):
        tags["cuisine"] = _unique(_normalize_cuisine_value(v) for v in tags["cuisine"])

    structured = {k: v for k, v in tags.items() if v}
    return structured, dropped


def migrate_recipe(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    changes: list[str] = []
    recipe_id = str(data.get("recipe_uuid", ""))

    flags = data.get("X-flags") or []
    if isinstance(flags, str):
        flags = [flags]
    is_reference = "index-page-not-a-recipe" in flags

    if data.get("author") and not data.get("source_authors"):
        author = data.pop("author")
        data["source_authors"] = [author] if isinstance(author, str) else list(author)
        changes.append(f"author → source_authors: {data['source_authors']}")

    legacy_cats = _legacy_categories(data)
    prior_categories = data.get("X-categories")

    if is_reference:
        if prior_categories != {"dish_type": ["reference"]}:
            data["X-categories"] = {"dish_type": ["reference"]}
            changes.append("X-categories.dish_type: [reference]")
    elif legacy_cats:
        dish_types, meal_types = _infer_dish_and_meal_types(recipe_id, legacy_cats)
        categories: dict[str, list[str]] = {"dish_type": dish_types}
        if meal_types:
            categories["meal_type"] = meal_types
        if "one_dish" in dish_types or recipe_id.endswith("shepherds-pie"):
            categories.setdefault("meal_role", []).append("one_dish_meal")
            categories["meal_role"] = _unique(categories["meal_role"])
        data["X-categories"] = categories
        changes.append(f"X-category {legacy_cats!r} → X-categories {categories}")
    elif not prior_categories and recipe_id in SPECIAL_DISH_TYPE:
        dish_types, meal_types = _infer_dish_and_meal_types(recipe_id, legacy_cats)
        categories = {"dish_type": dish_types}
        if meal_types:
            categories["meal_type"] = meal_types
        if "one_dish" in dish_types or recipe_id.endswith("shepherds-pie"):
            categories.setdefault("meal_role", []).append("one_dish_meal")
            categories["meal_role"] = _unique(categories["meal_role"])
        data["X-categories"] = categories
        changes.append(f"added X-categories {categories}")

    prior_tags = data.get("X-tags")
    structured_tags, dropped_tags = _build_structured_tags(data, legacy_cats)
    if structured_tags:
        data["X-tags"] = structured_tags
    elif "X-tags" in data:
        del data["X-tags"]

    if prior_tags != data.get("X-tags"):
        if structured_tags:
            changes.append(f"X-tags → {list(structured_tags.keys())}")
        else:
            changes.append("removed X-tags")
    if dropped_tags:
        changes.append(f"dropped flat tags: {dropped_tags}")

    for legacy_key in ("X-category", "X-dietary", "X-cuisine"):
        if legacy_key in data:
            del data[legacy_key]
            changes.append(f"removed {legacy_key}")

    if data.get("X-flags") == []:
        del data["X-flags"]
        changes.append("removed empty X-flags")

    if not is_reference and not data.get("X-source-verification"):
        data["X-source-verification"] = {"status": "needs-review", "notes": []}
        changes.append("added X-source-verification")

    changes.extend(_cleanup_dropped_fields(data))
    if _normalize_cuisine_in_tags(data):
        changes.append("normalized cuisine tags (dropped -inspired)")
    if _relocate_freezer_friendly(data):
        changes.append("freezer-friendly: planning → context")
    changes.extend(_migrate_handwritten_and_tips(data))

    return data, changes


def finalize_recipe(data: dict[str, Any]) -> dict[str, Any]:
    """Apply field ordering after all metadata mutations."""
    return reorder_recipe_fields(data)


def migrate_file(path: Path, *, dry_run: bool) -> list[str]:
    before = path.read_text(encoding="utf-8")
    data = yaml.safe_load(before)
    if not isinstance(data, dict):
        return [f"{path.name}: skip (not a mapping)"]

    migrated, changes = migrate_recipe(data)
    migrated = finalize_recipe(migrated)
    after_text = _dump_recipe(migrated)

    # Normalize trailing newline for comparison with on-disk content.
    before_cmp = before if before.endswith("\n") else before + "\n"

    if after_text == before_cmp and not changes:
        return [f"{path.name}: no changes"]

    if after_text != before_cmp and not any("reordered" in c for c in changes):
        changes.append("reordered fields (X-* at end)")

    if not dry_run:
        path.write_text(after_text, encoding="utf-8")

    recipe_id = migrated.get("recipe_uuid", path.stem)
    lines = [f"=== {recipe_id} ==="]
    lines.extend(f"  - {c}" for c in changes)
    if not dry_run:
        lines.append("  metadata after:")
        for key in ("X-categories", "X-tags", "X-source-verification", "source_authors"):
            if key in migrated:
                val = migrated[key]
                lines.append(f"    {key}: {yaml.dump(val, default_flow_style=True).strip()}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy recipe metadata")
    parser.add_argument(
        "directory",
        nargs="?",
        default=str(REPO / "recipes"),
        help="Directory of recipe YAML files (default: recipes/)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    directory = Path(args.directory)
    paths = sorted(directory.glob("wc-kitchen.*.yaml"))
    if not paths:
        print(f"No recipe files in {directory}", file=sys.stderr)
        return 1

    all_lines: list[str] = []
    changed = 0
    for path in paths:
        result = migrate_file(path, dry_run=args.dry_run)
        if len(result) > 1 or (len(result) == 1 and "no changes" not in result[0]):
            if "no changes" not in result[0]:
                changed += 1
        all_lines.extend(result)
        all_lines.append("")

    print("\n".join(all_lines))
    print(f"{'Would migrate' if args.dry_run else 'Migrated'} {changed} / {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
