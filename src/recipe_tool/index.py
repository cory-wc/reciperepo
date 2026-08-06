from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .load import load_recipe
from .paths import RepoPaths
from .render import get_jinja_env

MAIN_DISH_TYPES = {
    "main",
    "one_dish",
    "pasta",
    "bowl",
    "burgers+sandwiches",
    "soup",
}
SIDE_DISH_TYPES = {"side", "salad", "appetizer"}


def _yield_summary(data: dict[str, Any]) -> str:
    yields = data.get("yields") or []
    if not yields:
        return ""
    y = yields[0]
    amt = y.get("amount", "")
    unit = y.get("unit", "servings")
    return f"{amt} {unit}".strip()


def _source_type(data: dict[str, Any]) -> str:
    if data.get("source_url"):
        return "url"
    if data.get("X-original-source"):
        return "file"
    return "unknown"


def _verification_status(data: dict[str, Any]) -> str:
    ver = data.get("X-source-verification") or {}
    if isinstance(ver, dict):
        return ver.get("status", "unknown")
    return "unknown"


def _ingredient_names(data: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in data.get("ingredients") or []:
        if not isinstance(item, dict) or not item:
            continue
        name, detail = next(iter(item.items()))
        if not isinstance(detail, dict):
            continue
        normalized = str(name).replace("_", " ").strip()
        if normalized:
            names.append(normalized)
    return names


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _categories(data: dict[str, Any]) -> dict[str, list[str]]:
    raw = data.get("X-categories")
    if isinstance(raw, dict):
        return {
            "dish_type": _string_list(raw.get("dish_type")),
            "meal_type": _string_list(raw.get("meal_type")),
            "meal_role": _string_list(raw.get("meal_role")),
        }

    # Preserve compatibility with recipes that have not migrated yet.
    legacy = _string_list(data.get("X-category"))
    return {"dish_type": [], "meal_type": legacy, "meal_role": []}


def _flatten_tags(data: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    raw = data.get("X-tags")
    if isinstance(raw, dict):
        facets = {str(name): _string_list(values) for name, values in raw.items()}
        values = [value for facet_values in facets.values() for value in facet_values]
        return facets, values

    values = _string_list(raw)
    return ({"legacy": values} if values else {}), values


def category_filter_tabs(categories: dict[str, list[str]]) -> list[str]:
    dish_types = set(categories.get("dish_type") or [])
    meal_types = set(categories.get("meal_type") or [])
    tabs: list[str] = []
    if dish_types & MAIN_DISH_TYPES:
        tabs.append("main")
    if dish_types & SIDE_DISH_TYPES:
        tabs.append("sides")
    if "dessert" in dish_types or "dessert" in meal_types:
        tabs.append("dessert")
    if "breakfast_bake" in dish_types or "breakfast" in meal_types:
        tabs.append("breakfast")
    if "lunch" in meal_types:
        tabs.append("lunch")
    if "dinner" in meal_types:
        tabs.append("dinner")
    return tabs


def _is_reference(data: dict[str, Any]) -> bool:
    flags = _string_list(data.get("X-flags"))
    return "index-page-not-a-recipe" in flags


def build_index_entry(recipe_id: str, paths: RepoPaths) -> dict[str, Any]:
    _, data, _ = load_recipe(recipe_id, paths)
    categories = _categories(data)
    tag_facets, tags = _flatten_tags(data)
    return {
        "id": recipe_id,
        "name": data.get("recipe_name", recipe_id),
        "categories": categories,
        "category": [
            *categories["dish_type"],
            *categories["meal_type"],
            *categories["meal_role"],
        ],
        "filter_tabs": category_filter_tabs(categories),
        "tag_facets": tag_facets,
        "tags": tags,
        "dietary": tag_facets.get("dietary", _string_list(data.get("X-dietary"))),
        "is_reference": _is_reference(data),
        "ingredients": _ingredient_names(data),
        "yield": _yield_summary(data),
        "source": _source_type(data),
        "verification": _verification_status(data),
        "links": {
            "html": f"site/{recipe_id}.html",
            "pdf": f"pdfs/{recipe_id}.pdf",
            "yaml": f"recipes/{recipe_id}.yaml",
        },
    }


def _sort_key(entry: dict[str, Any], by: str) -> tuple:
    if by == "tag":
        tags = entry.get("tags") or ["untagged"]
        return (str(tags[0]).lower(), entry["name"].lower())
    if by == "category":
        cats = entry.get("category") or ["uncategorized"]
        return (str(cats[0]).lower(), entry["name"].lower())
    return (entry["name"].lower(),)


def build_index(
    paths: RepoPaths | None = None,
    by: str = "name",
    allow_missing: bool = False,
) -> dict[str, Any]:
    paths = paths or RepoPaths()
    entries = [
        entry
        for rid in paths.list_recipe_ids()
        if not (entry := build_index_entry(rid, paths))["is_reference"]
    ]
    uncategorized = [entry["id"] for entry in entries if not entry["filter_tabs"]]
    if uncategorized:
        raise ValueError(
            "Every recipe must belong to at least one category filter tab. "
            "Update X-categories for:\n" + "\n".join(uncategorized)
        )
    entries.sort(key=lambda e: _sort_key(e, by))

    warnings: list[str] = []
    for entry in entries:
        html_path = paths.root / entry["links"]["html"]
        pdf_path = paths.root / entry["links"]["pdf"]
        yaml_path = paths.recipe_yaml(entry["id"])
        yaml_mtime = yaml_path.stat().st_mtime if yaml_path.exists() else 0
        for label, artifact in [("html", html_path), ("pdf", pdf_path)]:
            if not artifact.exists():
                msg = f"{entry['id']}: missing {label} at {artifact.relative_to(paths.root)}"
                warnings.append(msg)
            elif artifact.stat().st_mtime < yaml_mtime:
                msg = f"{entry['id']}: stale {label} (older than YAML)"
                warnings.append(msg)

    if warnings and not allow_missing:
        raise FileNotFoundError(
            "Index artifacts missing or stale. Run `recipe render` and `recipe pdf` first, "
            "or pass --allow-missing.\n" + "\n".join(warnings)
        )

    index_data = {
        "generated_at": date.today().isoformat(),
        "sort_by": by,
        "recipes": entries,
    }
    if warnings:
        index_data["warnings"] = warnings

    paths.index_yaml().write_text(
        yaml.dump(index_data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return index_data


def render_index_html(
    paths: RepoPaths | None = None,
    mode: str = "screen",
    by: str = "name",
    output_path: Path | None = None,
    allow_missing: bool = False,
) -> str:
    paths = paths or RepoPaths()
    index_data = build_index(paths, by=by, allow_missing=allow_missing)
    env = get_jinja_env(paths)
    template = env.get_template("index.html.j2")
    html = template.render(
        title="Willineau Recipes",
        mode=mode,
        generated_at=index_data["generated_at"],
        recipes=index_data["recipes"],
        sort_by=by,
    )
    dest = output_path or paths.index_html()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return html


def generate_index(
    paths: RepoPaths | None = None,
    by: str = "name",
    allow_missing: bool = False,
    include_pdf: bool = True,
) -> None:
    paths = paths or RepoPaths()
    build_index(paths, by=by, allow_missing=allow_missing)
    render_index_html(paths, mode="screen", by=by, allow_missing=allow_missing)
    if include_pdf and paths.list_recipe_ids():
        from .pdf import generate_index_pdf

        generate_index_pdf(paths)
