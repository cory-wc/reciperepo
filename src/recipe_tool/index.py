from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .load import load_recipe
from .paths import RepoPaths
from .render import get_jinja_env


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


def build_index_entry(recipe_id: str, paths: RepoPaths) -> dict[str, Any]:
    _, data, _ = load_recipe(recipe_id, paths)
    return {
        "id": recipe_id,
        "name": data.get("recipe_name", recipe_id),
        "category": data.get("X-category") or [],
        "tags": data.get("X-tags") or [],
        "dietary": data.get("X-dietary") or [],
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
        return (tags[0].lower(), entry["name"].lower())
    if by == "category":
        cats = entry.get("category") or ["uncategorized"]
        return (cats[0].lower(), entry["name"].lower())
    return (entry["name"].lower(),)


def build_index(
    paths: RepoPaths | None = None,
    by: str = "name",
    allow_missing: bool = False,
) -> dict[str, Any]:
    paths = paths or RepoPaths()
    entries = [build_index_entry(rid, paths) for rid in paths.list_recipe_ids()]
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
        title="Recipe Index",
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
