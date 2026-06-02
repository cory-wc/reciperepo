from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .load import load_recipe
from .metadata_facets import (
    FACET_LABELS,
    TAG_FACET_KEYS,
    build_filter_tree,
    extract_facets,
    facet_tokens,
    facets_summary,
    is_filterable_metadata,
    is_reference_entry,
    metadata_cleanup_issues,
)
from .paths import RepoPaths
from .render import get_jinja_env

_FILTER_JS_SOURCE = Path(__file__).resolve().parents[2] / "templates" / "index-filter.js"


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


def _links(recipe_id: str) -> dict[str, str]:
    return {
        "html": f"site/{recipe_id}.html",
        "pdf": f"pdfs/{recipe_id}.pdf",
        "yaml": f"recipes/{recipe_id}.yaml",
    }


def _structured_categories(facets: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        k: facets[k]
        for k in ("dish_type", "meal_type", "meal_role")
        if facets.get(k)
    }


def _structured_tags(facets: dict[str, list[str]]) -> dict[str, list[str]]:
    return {k: facets[k] for k in TAG_FACET_KEYS if facets.get(k)}


def build_index_entry(recipe_id: str, data: dict[str, Any]) -> dict[str, Any]:
    facets = extract_facets(data)
    reference = is_reference_entry(data)
    return {
        "id": recipe_id,
        "name": data.get("recipe_name", recipe_id),
        "categories": _structured_categories(facets),
        "tags": _structured_tags(facets),
        "facets": facets,
        "facet_tokens": facet_tokens(facets),
        "facets_summary": facets_summary(facets),
        "is_reference": reference,
        "yield": _yield_summary(data),
        "source": _source_type(data),
        "verification": _verification_status(data),
        "links": _links(recipe_id),
    }


def build_cleanup_entry(recipe_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": recipe_id,
        "name": data.get("recipe_name", recipe_id),
        "issues": metadata_cleanup_issues(data),
        "yield": _yield_summary(data),
        "links": _links(recipe_id),
    }


def _sort_key(entry: dict[str, Any], by: str) -> tuple:
    if by == "tag":
        tags = entry.get("tags") or {}
        all_vals: list[str] = []
        for vals in tags.values():
            all_vals.extend(vals)
        first = sorted(all_vals)[0] if all_vals else "untagged"
        return (first.lower(), entry["name"].lower())
    if by == "category":
        cats = entry.get("categories") or {}
        dish = cats.get("dish_type") or ["uncategorized"]
        return (dish[0].lower(), entry["name"].lower())
    return (entry["name"].lower(),)


def build_index(
    paths: RepoPaths | None = None,
    by: str = "name",
    allow_missing: bool = False,
) -> dict[str, Any]:
    paths = paths or RepoPaths()
    recipes: list[dict[str, Any]] = []
    needs_cleanup: list[dict[str, Any]] = []

    for recipe_id in paths.list_recipe_ids():
        _, data, _ = load_recipe(recipe_id, paths)
        if is_filterable_metadata(data):
            recipes.append(build_index_entry(recipe_id, data))
        else:
            needs_cleanup.append(build_cleanup_entry(recipe_id, data))

    recipes.sort(key=lambda e: _sort_key(e, by))
    needs_cleanup.sort(key=lambda e: e["name"].lower())

    warnings: list[str] = []
    all_entries = recipes + [
        {
            "id": e["id"],
            "links": e["links"],
        }
        for e in needs_cleanup
    ]
    for entry in all_entries:
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
        "recipes": recipes,
        "needs_cleanup": needs_cleanup,
        "filter_tree": build_filter_tree(recipes),
    }
    if warnings:
        index_data["warnings"] = warnings

    paths.index_yaml().write_text(
        yaml.dump(index_data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return index_data


def _copy_index_filter_js(paths: RepoPaths) -> None:
    if _FILTER_JS_SOURCE.is_file():
        dest = paths.site / "index-filter.js"
        shutil.copy2(_FILTER_JS_SOURCE, dest)


def render_index_html(
    paths: RepoPaths | None = None,
    mode: str = "screen",
    by: str = "name",
    output_path: Path | None = None,
    allow_missing: bool = False,
) -> str:
    paths = paths or RepoPaths()
    index_data = build_index(paths, by=by, allow_missing=allow_missing)
    if mode == "screen":
        _copy_index_filter_js(paths)

    env = get_jinja_env(paths)
    template = env.get_template("index.html.j2")

    if mode == "print":
        # Print binder lists every recipe; cleanup entries omit facet column data.
        print_recipes = list(index_data["recipes"])
        for entry in index_data.get("needs_cleanup", []):
            print_recipes.append(
                {
                    **entry,
                    "facets_summary": "needs metadata cleanup",
                    "is_reference": False,
                }
            )
        print_recipes.sort(key=lambda e: e["name"].lower())
        table_recipes = print_recipes
    else:
        table_recipes = index_data["recipes"]

    html = template.render(
        title="Recipe Index",
        mode=mode,
        generated_at=index_data["generated_at"],
        recipes=table_recipes,
        needs_cleanup=index_data.get("needs_cleanup", []),
        sort_by=by,
        filter_tree=index_data.get("filter_tree", []),
        facet_labels=FACET_LABELS,
        browsable_count=sum(1 for r in index_data["recipes"] if not r.get("is_reference")),
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
    index_data = build_index(paths, by=by, allow_missing=allow_missing)
    render_index_html(paths, mode="screen", by=by, allow_missing=allow_missing)
    cleanup_count = len(index_data.get("needs_cleanup", []))
    if cleanup_count:
        ids = ", ".join(e["id"] for e in index_data["needs_cleanup"])
        print(f"Index: {len(index_data['recipes'])} filterable recipes; "
              f"{cleanup_count} need metadata cleanup: {ids}")
    if include_pdf and paths.list_recipe_ids():
        from .pdf import generate_index_pdf

        generate_index_pdf(paths)
