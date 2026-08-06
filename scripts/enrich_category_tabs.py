#!/usr/bin/env python3
"""Audit and conservatively enrich recipe categories from source pages."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from recipe_tool.index import category_filter_tabs
from recipe_tool.paths import RepoPaths

USER_AGENT = "recipe-tool/0.1 category-enrichment"

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


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _find_recipe_node(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if "Recipe" in str(value.get("@type", "")):
            return value
        for nested in value.values():
            recipe = _find_recipe_node(nested)
            if recipe:
                return recipe
    elif isinstance(value, list):
        for nested in value:
            recipe = _find_recipe_node(nested)
            if recipe:
                return recipe
    return None


def _recipe_json_ld(html: str) -> dict[str, Any] | None:
    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    )
    for script in scripts:
        try:
            recipe = _find_recipe_node(json.loads(script.strip()))
        except (json.JSONDecodeError, TypeError):
            continue
        if recipe:
            return recipe
    return None


def _page_signals(html: str, recipe: dict[str, Any] | None) -> list[str]:
    values: list[str] = []
    if recipe:
        for key in ("recipeCategory", "keywords", "name"):
            values.extend(_string_list(recipe.get(key)))

    for pattern in (
        r"<title[^>]*>(.*?)</title>",
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:title["\']',
    ):
        match = re.search(pattern, html, re.I | re.S)
        if match:
            values.append(re.sub(r"\s+", " ", match.group(1)).strip())
    return list(dict.fromkeys(value for value in values if value))


def _source_suggestions(signals: list[str]) -> dict[str, list[str]]:
    suggestions: dict[str, list[str]] = {"dish_type": [], "meal_type": []}
    signal_text = " | ".join(signals)
    for pattern, facet, value in SIGNAL_RULES:
        if pattern.search(signal_text) and value not in suggestions[facet]:
            suggestions[facet].append(value)
    return suggestions


def _apply_source_suggestions(data: dict[str, Any], suggestions: dict[str, list[str]]) -> list[str]:
    categories = data.setdefault("X-categories", {})
    changes: list[str] = []
    for facet, values in suggestions.items():
        current = _string_list(categories.get(facet))
        for value in values:
            # Keep source inference conservative: meal occasions are safely additive.
            # For dish type, only add a source-specific appetizer classification.
            if value not in current and (facet == "meal_type" or value == "appetizer"):
                current.append(value)
                changes.append(f"add {facet}:{value} from source")
        categories[facet] = current
    return changes


def _ensure_tab_coverage(data: dict[str, Any]) -> list[str]:
    categories = data.setdefault("X-categories", {})
    dish_types = _string_list(categories.get("dish_type"))
    meal_types = _string_list(categories.get("meal_type"))
    normalized = {
        "dish_type": dish_types,
        "meal_type": meal_types,
        "meal_role": _string_list(categories.get("meal_role")),
    }
    if category_filter_tabs(normalized):
        return []

    changes: list[str] = []
    if set(dish_types) & {"sauce", "preserve", "component"}:
        dish_types.append("side")
        changes.append("add dish_type:side for category-tab coverage")
    elif "beverage" in dish_types:
        meal_types.append("dinner")
        changes.append("add meal_type:dinner for category-tab coverage")
    elif "bread" in dish_types:
        meal_types.append("breakfast")
        changes.append("add meal_type:breakfast for category-tab coverage")
    else:
        meal_types.append("lunch")
        changes.append("add meal_type:lunch for category-tab coverage")

    categories["dish_type"] = list(dict.fromkeys(dish_types))
    categories["meal_type"] = list(dict.fromkeys(meal_types))
    return changes


def _is_reference(data: dict[str, Any]) -> bool:
    return "index-page-not-a-recipe" in _string_list(data.get("X-flags"))


def _analyze_source(source_url: str) -> tuple[str, list[str], dict[str, list[str]]]:
    try:
        result = subprocess.run(
            [
                "curl",
                "--location",
                "--fail",
                "--silent",
                "--show-error",
                "--compressed",
                "--max-time",
                "8",
                "--user-agent",
                USER_AGENT,
                source_url,
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        recipe = _recipe_json_ld(result.stdout)
        signals = _page_signals(result.stdout, recipe)
        return "analyzed", signals, _source_suggestions(signals)
    except (subprocess.SubprocessError, OSError) as exc:
        signals = [source_url]
        return f"error: {exc}", signals, _source_suggestions(signals)


def _add_lunch_candidates(data: dict[str, Any]) -> list[str]:
    categories = data.setdefault("X-categories", {})
    dish_types = set(_string_list(categories.get("dish_type")))
    meal_types = _string_list(categories.get("meal_type"))
    if not dish_types & {"soup", "salad", "bowl", "burgers+sandwiches"}:
        return []
    if "lunch" in meal_types:
        return []
    meal_types.append("lunch")
    categories["meal_type"] = meal_types
    return ["add meal_type:lunch from lunch-friendly dish type"]


def _improve_obvious_names(data: dict[str, Any]) -> list[str]:
    name = str(data.get("recipe_name", "")).lower()
    categories = data.setdefault("X-categories", {})
    dish_types = set(_string_list(categories.get("dish_type")))
    meal_types = _string_list(categories.get("meal_type"))
    changes: list[str] = []

    breakfast_name = any(word in name for word in ("breakfast", "muffin", "waffle", "pancake"))
    sweet_quick_bread = "bread" in dish_types and "zucchini bread" in name
    if (breakfast_name or sweet_quick_bread) and "breakfast" not in meal_types:
        meal_types.append("breakfast")
        changes.append("add meal_type:breakfast from recipe name")
    if (breakfast_name or sweet_quick_bread) and "dinner" in meal_types:
        meal_types.remove("dinner")
        changes.append("remove meal_type:dinner contradicted by recipe name")

    categories["meal_type"] = meal_types
    return changes


def enrich(paths: RepoPaths, *, apply: bool) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    records: list[tuple[str, Path, dict[str, Any]]] = []
    for recipe_id in paths.list_recipe_ids():
        yaml_path = paths.recipe_yaml(recipe_id)
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and not _is_reference(data):
            records.append((recipe_id, yaml_path, data))

    source_results: dict[str, tuple[str, list[str], dict[str, list[str]]]] = {}
    with ThreadPoolExecutor(max_workers=16) as executor:
        future_urls = {
            executor.submit(_analyze_source, str(data["source_url"])): recipe_id
            for recipe_id, _, data in records
            if data.get("source_url")
        }
        for future in as_completed(future_urls):
            source_results[future_urls[future]] = future.result()

    for recipe_id, yaml_path, data in records:
        source_url = data.get("source_url")
        source_status, signals, suggestions = source_results.get(
            recipe_id,
            ("no-source-url", [], {"dish_type": [], "meal_type": []}),
        )
        changes = _apply_source_suggestions(data, suggestions)
        changes.extend(_improve_obvious_names(data))
        changes.extend(_add_lunch_candidates(data))
        changes.extend(_ensure_tab_coverage(data))
        categories = data.get("X-categories") or {}
        filter_tabs = category_filter_tabs(
            {
                "dish_type": _string_list(categories.get("dish_type")),
                "meal_type": _string_list(categories.get("meal_type")),
                "meal_role": _string_list(categories.get("meal_role")),
            }
        )
        if apply and changes:
            yaml_path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

        report.append(
            {
                "recipe_id": recipe_id,
                "source_url": source_url,
                "source_status": source_status,
                "source_signals": signals,
                "suggestions": suggestions,
                "changes": changes,
                "filter_tabs": filter_tabs,
            }
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze source pages and ensure every recipe maps to a category tab."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write conservative source-derived and coverage changes to recipe YAML.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Write the full JSON report to this path; otherwise print it.",
    )
    args = parser.parse_args()

    report = enrich(RepoPaths(), apply=args.apply)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
        print(f"Wrote {args.report}")
    else:
        print(output, end="")

    analyzed = sum(item["source_status"] == "analyzed" for item in report)
    source_errors = sum(str(item["source_status"]).startswith("error:") for item in report)
    changed = sum(bool(item["changes"]) for item in report)
    print(
        f"Analyzed {analyzed} source page(s); "
        f"{source_errors} source fetch error(s); "
        f"{changed} recipe(s) would change."
    )
    missing = [item["recipe_id"] for item in report if not item["filter_tabs"]]
    if missing:
        print("Recipes without category-tab coverage: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
