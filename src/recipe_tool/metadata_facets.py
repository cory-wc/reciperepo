"""Extract taxonomy facets from structured recipe metadata for index filtering."""

from __future__ import annotations

from typing import Any

# Facet keys used in filter UI (order = tree display order).
CATEGORY_FACET_KEYS = ("dish_type", "meal_type", "meal_role")
TAG_FACET_KEYS = (
    "cuisine",
    "dietary",
    "method",
    "context",
    "season",
    "primary_ingredient",
    "flavor_profile",
)
FACET_KEYS = CATEGORY_FACET_KEYS + TAG_FACET_KEYS

FACET_LABELS: dict[str, str] = {
    "dish_type": "Dish type",
    "meal_type": "Meal type",
    "meal_role": "Meal role",
    "cuisine": "Cuisine",
    "dietary": "Dietary",
    "method": "Method",
    "context": "Context",
    "season": "Season",
    "primary_ingredient": "Primary ingredient",
    "flavor_profile": "Flavor profile",
}


def _as_list(value: Any) -> list[str]:
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, str):
        if "," in value:
            return [p.strip() for p in value.split(",") if p.strip()]
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None and not isinstance(v, bool)]
    return [str(value)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        key = norm_token(v)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def norm_token(value: str) -> str:
    """Normalize a facet value to snake_case."""
    v = value.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in v:
        v = v.replace("__", "_")
    return v


def is_reference_entry(data: dict[str, Any]) -> bool:
    flags = data.get("X-flags") or []
    if isinstance(flags, str):
        flags = [flags]
    if "index-page-not-a-recipe" in flags:
        return True
    categories = data.get("X-categories")
    if isinstance(categories, dict):
        dish = [norm_token(d) for d in _as_list(categories.get("dish_type"))]
        if "reference" in dish:
            return True
    return False


def metadata_cleanup_issues(data: dict[str, Any]) -> list[str]:
    """Return reasons this recipe is not ready for index filtering."""
    if is_reference_entry(data):
        categories = data.get("X-categories")
        if isinstance(categories, dict):
            dish = [norm_token(d) for d in _as_list(categories.get("dish_type"))]
            if "reference" in dish:
                return []
        if data.get("X-category") is not None:
            return ["legacy X-category (use X-categories.dish_type: [reference])"]
        return ["missing X-categories.dish_type: [reference]"]

    issues: list[str] = []
    if data.get("X-category") is not None:
        issues.append("legacy X-category")
    if data.get("X-dietary") is not None:
        issues.append("legacy X-dietary")
    if data.get("X-cuisine") is not None:
        issues.append("legacy X-cuisine")

    tags = data.get("X-tags")
    if isinstance(tags, list):
        issues.append("flat X-tags list (use structured X-tags)")

    categories = data.get("X-categories")
    if not isinstance(categories, dict):
        issues.append("missing X-categories")
    else:
        if not _as_list(categories.get("dish_type")):
            issues.append("missing X-categories.dish_type")
        if not _as_list(categories.get("meal_type")):
            issues.append("missing X-categories.meal_type")

    return issues


def is_filterable_metadata(data: dict[str, Any]) -> bool:
    return not metadata_cleanup_issues(data)


def extract_facets(data: dict[str, Any]) -> dict[str, list[str]]:
    """Return facet key → normalized values from structured metadata only."""
    facets: dict[str, list[str]] = {k: [] for k in FACET_KEYS}

    categories = data.get("X-categories")
    if isinstance(categories, dict):
        for key in CATEGORY_FACET_KEYS:
            facets[key].extend(norm_token(v) for v in _as_list(categories.get(key)))

    tags = data.get("X-tags")
    if isinstance(tags, dict):
        for key in TAG_FACET_KEYS:
            if key in tags:
                facets[key].extend(norm_token(v) for v in _as_list(tags.get(key)))
        for v in _as_list(tags.get("planning")):
            token = norm_token(v)
            if token == "freezer-friendly":
                token = "freezer_friendly"
            facets["context"].append(token)

    for key in FACET_KEYS:
        facets[key] = _unique(facets[key])
    return {k: v for k, v in facets.items() if v}


def facet_tokens(facets: dict[str, list[str]]) -> list[str]:
    """Flat tokens for data-facets: dish_type:soup, cuisine:japanese, …"""
    tokens: list[str] = []
    for key in FACET_KEYS:
        for value in facets.get(key, []):
            tokens.append(f"{key}:{value}")
    return tokens


def facets_summary(facets: dict[str, list[str]], max_values: int = 8) -> str:
    """Compact display string for table column."""
    parts: list[str] = []
    for key in FACET_KEYS:
        for value in facets.get(key, []):
            parts.append(format_value_label(value))
            if len(parts) >= max_values:
                return " · ".join(parts)
    return " · ".join(parts)


def format_value_label(value: str) -> str:
    if value == "burgers+sandwiches":
        return "Burgers & sandwiches"
    return value.replace("_", " ").replace("+", " + ")


def build_filter_tree(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build filter tree from index entries (each has facets dict)."""
    counts: dict[str, dict[str, int]] = {k: {} for k in FACET_KEYS}
    for entry in entries:
        if entry.get("is_reference"):
            continue
        for key in FACET_KEYS:
            for value in (entry.get("facets") or {}).get(key, []):
                counts[key][value] = counts[key].get(value, 0) + 1

    groups: list[dict[str, Any]] = []
    for key in FACET_KEYS:
        value_counts = counts[key]
        if not value_counts:
            continue
        options = [
            {
                "value": v,
                "label": format_value_label(v),
                "count": value_counts[v],
                "token": f"{key}:{v}",
            }
            for v in sorted(value_counts.keys(), key=lambda x: (x.replace("+", " "), x))
        ]
        groups.append(
            {
                "key": key,
                "label": FACET_LABELS[key],
                "options": options,
            }
        )
    return groups


def recipe_matches_filters(
    facet_tokens_list: list[str],
    selected: dict[str, set[str]],
) -> bool:
    """AND across facets with selections; OR within each facet."""
    if not selected:
        return True
    token_set = set(facet_tokens_list)
    for facet_key, values in selected.items():
        if not values:
            continue
        if not any(f"{facet_key}:{v}" in token_set for v in values):
            return False
    return True
