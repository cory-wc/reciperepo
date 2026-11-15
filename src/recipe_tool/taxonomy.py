"""Category and tag rules shared with the metadata scripts.

URL ingest calls these directly. The batch scripts keep their own copies for now.
"""

from __future__ import annotations

import re
from typing import Any

SIGNAL_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\b(appetizer|starter|hors d'oeuvre)\b", re.I), "dish_type", "appetizer"),
    (re.compile(r"\b(side dish|side)\b", re.I), "dish_type", "side"),
    (re.compile(r"\b(soup|stew|chowder|chili)\b", re.I), "dish_type", "soup"),
    (re.compile(r"\bsalad\b", re.I), "dish_type", "salad"),
    (re.compile(r"\b(main course|main dish|entrée|entree)\b", re.I), "dish_type", "main"),
    (re.compile(r"\b(dessert|cake|cookie|pastry)\b", re.I), "dish_type", "dessert"),
    (re.compile(r"\b(breakfast|brunch)\b", re.I), "meal_type", "breakfast"),
    (re.compile(r"\blunch\b", re.I), "meal_type", "lunch"),
    (re.compile(r"\b(dinner|supper)\b", re.I), "meal_type", "dinner"),
)

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

SLOW_COOKER_RE = re.compile(
    r"\b(?:slow[\s-]?cooker|crock[\s-]?pot|crockpot)\b",
    re.IGNORECASE,
)
INSTANT_POT_RE = re.compile(r"\binstant[\s-]?pot\b", re.IGNORECASE)
OVEN_TEMP_RE = re.compile(
    r"(?:"
    r"preheat(?:\s+the|\s+your)?\s+oven\s+to\s+\d+"
    r"|heat\s+oven\s+to\s+\d+"
    r"|\d+\s*(?:°|degrees?(?:\s+(?:[FCfc]|Fahrenheit|Celsius))?)\s+oven\b"
    r"|\boven\s+temperature\s+to\s+\d+"
    r"|\bbake\s+(?:at|in\s+(?:the\s+|a\s+)?(?:preheated\s+)?)\d+"
    r")",
    re.IGNORECASE,
)
OVEN_MENTION_RE = re.compile(r"\boven\b", re.IGNORECASE)
BURGER_CARRIER_SCRUB_RE = re.compile(r"bread\s*crumbs?|breadcrumbs?", re.IGNORECASE)
BURGER_CARRIER_RE = re.compile(r"\b(?:buns?|tortillas?|bread)\b", re.IGNORECASE)

DIETARY_FALSE_POSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"non[\s-]?vegan[\s-]?vegetarian[\s-]?friendly",
        r"vegan[\s-]?vegetarian[\s-]?friendly",
        r"vegetarian[\s-]?adaptable",
        r"vegan[\s-]?adaptable",
        r"non[\s-]?vegan",
        r"non[\s-]?vegetarian",
        r"not[\s-]?vegan",
        r"not[\s-]?vegetarian",
        r"vegetarian oyster sauce",
        r"\bto make vegetarian\b",
        r"\bto make vegan\b",
        r"\bfor vegan\b",
        r"\bfor vegetarian\b",
        r"\bmake it vegetarian\b",
        r"\bmake it vegan\b",
        r"\bvegetarian version\b",
        r"\bvegan version\b",
        r"\bvegan parmesan\b",
    )
)

KNOWN_CUISINES = {
    "american",
    "italian",
    "thai",
    "indian",
    "mexican",
    "chinese",
    "japanese",
    "korean",
    "french",
    "german",
    "mediterranean",
    "middle_eastern",
    "greek",
    "cajun",
    "scandinavian",
    "seafood",
}
PRIMARY_INGREDIENTS = (
    "potatoes",
    "chickpeas",
    "chicken",
    "beef",
    "pork",
    "fish",
    "beans",
    "tofu",
    "squash",
    "pasta",
    "rice",
    "mushrooms",
    "eggs",
    "turkey",
    "lamb",
    "shrimp",
    "salmon",
)
CONTEXT_VALUES = {
    "weeknight",
    "quick",
    "comfort_food",
    "holiday",
    "entertaining",
    "freezer-friendly",
    "make_ahead",
    "meal_prep",
    "leftovers_friendly",
}
SEASON_VALUES = {"spring", "summer", "fall", "winter"}
FLAVOR_VALUES = {"savory", "hearty", "spicy", "sweet", "tangy", "creamy", "smoky", "fresh"}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def normalize_cuisine_value(value: str) -> str:
    """Cuisine tags use base names only (japanese, not japanese_inspired)."""
    normalized = value.replace("-", "_").lower().strip()
    if normalized.endswith("_inspired"):
        normalized = normalized[: -len("_inspired")]
    return normalized


def _recipe_search_text(data: dict[str, Any]) -> str:
    parts: list[str] = [
        str(data.get("recipe_name", "")),
        str(data.get("recipe_uuid", "")),
        str(data.get("description", "")),
    ]
    for step in data.get("steps") or []:
        if isinstance(step, dict):
            parts.append(str(step.get("step", "")))
            parts.extend(str(note) for note in step.get("notes") or [])
        else:
            parts.append(str(step))
    for item in data.get("ingredients") or []:
        if not isinstance(item, dict):
            continue
        for name, body in item.items():
            parts.append(str(name))
            if not isinstance(body, dict):
                continue
            notes = body.get("notes") or []
            if isinstance(notes, str):
                notes = [notes]
            parts.extend(str(note) for note in notes)
            parts.extend(str(proc) for proc in body.get("processing") or [])
    return " ".join(parts)


def _oven_search_text(data: dict[str, Any], extra: str = "") -> str:
    text = f"{_recipe_search_text(data)} {extra}"
    return re.sub(r"\bdutch\s+oven\b", " ", text, flags=re.IGNORECASE)


def infer_methods(data: dict[str, Any], extra: str = "") -> list[str]:
    text = _oven_search_text(data, extra)
    methods: list[str] = []
    if SLOW_COOKER_RE.search(text):
        methods.append("slow_cooker")
    if INSTANT_POT_RE.search(text):
        methods.append("instant_pot")
    if OVEN_TEMP_RE.search(text) or OVEN_MENTION_RE.search(text):
        methods.append("oven")
    folded = text.lower()
    for phrase, tag in sorted(METHOD_TAGS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", folded):
            methods.append(tag)
    return _unique(methods)


def _scrub_dietary(text: str) -> str:
    for pattern in DIETARY_FALSE_POSITIVE_PATTERNS:
        text = pattern.sub(" ", text)
    return text


def infer_dietary(data: dict[str, Any]) -> list[str]:
    text = _scrub_dietary(_recipe_search_text(data))
    dietary: list[str] = []
    if re.search(r"\bvegan\b", text, re.IGNORECASE):
        dietary.append("vegan")
    if re.search(r"\bvegetarian\b", text, re.IGNORECASE):
        dietary.append("vegetarian")
    if "vegan" in dietary and "vegetarian" not in dietary:
        dietary.append("vegetarian")
    return dietary


def _signal_suggestions(signals: list[str]) -> dict[str, list[str]]:
    suggestions: dict[str, list[str]] = {"dish_type": [], "meal_type": []}
    signal_text = " | ".join(signals)
    for pattern, facet, value in SIGNAL_RULES:
        if pattern.search(signal_text) and value not in suggestions[facet]:
            suggestions[facet].append(value)
    return suggestions


def _improve_obvious_names(data: dict[str, Any]) -> None:
    name = str(data.get("recipe_name", "")).lower()
    categories = data.setdefault("X-categories", {})
    dish_types = set(categories.get("dish_type") or [])
    meal_types = list(categories.get("meal_type") or [])
    breakfast_name = any(word in name for word in ("breakfast", "muffin", "waffle", "pancake"))
    sweet_quick_bread = "bread" in dish_types and "zucchini bread" in name
    if (breakfast_name or sweet_quick_bread) and "breakfast" not in meal_types:
        meal_types.append("breakfast")
    if (breakfast_name or sweet_quick_bread) and "dinner" in meal_types:
        meal_types.remove("dinner")
    categories["meal_type"] = meal_types


def _add_lunch_candidates(data: dict[str, Any]) -> None:
    categories = data.setdefault("X-categories", {})
    dish_types = set(categories.get("dish_type") or [])
    meal_types = list(categories.get("meal_type") or [])
    if not dish_types & {"soup", "salad", "bowl", "burgers+sandwiches"}:
        return
    if "lunch" not in meal_types:
        meal_types.append("lunch")
        categories["meal_type"] = meal_types


def _burgers_sandwiches(data: dict[str, Any]) -> bool:
    recipe_id = str(data.get("recipe_uuid", ""))
    slug = recipe_id.removeprefix("wc-kitchen.").replace("-", " ")
    text = f"{data.get('recipe_name', '')} {slug}".lower()
    if "macaroni" in text and "hamburger" in text:
        return False
    named = any(
        word in text
        for word in (
            "burger",
            "burgers",
            "sloppy joe",
            "sloppy joes",
            "sandwich",
            "wraps",
            "quesadilla",
            "quesadillas",
        )
    )
    if not named:
        return False
    body = BURGER_CARRIER_SCRUB_RE.sub(" ", _recipe_search_text(data))
    return bool(BURGER_CARRIER_RE.search(body))


def _primary_ingredients(data: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in data.get("ingredients") or []:
        if isinstance(item, dict):
            names.extend(str(name).lower() for name in item)
    found: list[str] = []
    for staple in PRIMARY_INGREDIENTS:
        if any(re.search(rf"\b{re.escape(staple)}\b", name) for name in names):
            found.append(staple)
        if len(found) == 2:
            break
    return found


def _facet_hits(tokens: list[str], allowed: set[str]) -> list[str]:
    hits: list[str] = []
    for token in tokens:
        key = token.strip().lower().replace(" ", "_").replace("-", "_")
        if key == "freezer_friendly":
            key = "freezer-friendly"
        if key in allowed and key not in hits:
            hits.append(key)
    return hits


def apply_taxonomy(
    data: dict[str, Any],
    *,
    categories: list[str],
    keywords: list[str],
    cuisines: list[str],
) -> None:
    """Fill X-categories and X-tags from page signals and recipe text."""
    signals = [str(data.get("recipe_name", "")), *categories, *keywords]
    suggestions = _signal_suggestions(signals)
    data["X-categories"] = {
        "dish_type": list(suggestions["dish_type"]),
        "meal_type": list(suggestions["meal_type"]),
    }
    _improve_obvious_names(data)
    if _burgers_sandwiches(data):
        data["X-categories"]["dish_type"] = ["burgers+sandwiches"]
    _add_lunch_candidates(data)

    tags: dict[str, list[str]] = {}
    cuisine_values = _unique(
        [
            normalize_cuisine_value(value)
            for value in [*cuisines, *keywords]
            if normalize_cuisine_value(value) in KNOWN_CUISINES
        ]
    )
    if cuisine_values:
        tags["cuisine"] = cuisine_values
    methods = infer_methods(data, extra=" ".join([*categories, *keywords]))
    if methods:
        tags["method"] = methods
    dietary = infer_dietary(data)
    if dietary:
        tags["dietary"] = dietary
    staples = _primary_ingredients(data)
    if staples:
        tags["primary_ingredient"] = staples
    tokens = [*categories, *keywords]
    for key, allowed in (
        ("context", CONTEXT_VALUES),
        ("season", SEASON_VALUES),
        ("flavor_profile", FLAVOR_VALUES),
    ):
        hits = _facet_hits(tokens, allowed)
        if hits:
            tags[key] = hits
    if tags:
        data["X-tags"] = tags

    categories_out = data["X-categories"]
    if not categories_out.get("dish_type"):
        del categories_out["dish_type"]
    if not categories_out.get("meal_type"):
        del categories_out["meal_type"]
    if not categories_out:
        del data["X-categories"]
