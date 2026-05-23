from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .load import load_recipe
from .paths import RepoPaths


@dataclass
class StatusLine:
    recipe_id: str
    kind: str
    message: str


def recipe_status(recipe_id: str, paths: RepoPaths) -> list[StatusLine]:
    lines: list[StatusLine] = []
    yaml_path = paths.recipe_yaml(recipe_id)
    if not yaml_path.exists():
        return [StatusLine(recipe_id, "error", "missing YAML")]

    yaml_mtime = yaml_path.stat().st_mtime
    for label, path in [
        ("pdf", paths.recipe_pdf(recipe_id)),
        ("html", paths.recipe_html(recipe_id)),
    ]:
        if not path.exists():
            lines.append(StatusLine(recipe_id, "missing", f"missing {label}"))
        elif path.stat().st_mtime < yaml_mtime:
            lines.append(StatusLine(recipe_id, "stale", f"stale {label}"))

    try:
        _, data, _ = load_recipe(recipe_id, paths)
        ver = data.get("X-source-verification") or {}
        if isinstance(ver, dict) and ver.get("status") == "needs-review":
            lines.append(StatusLine(recipe_id, "review", "needs-review"))
    except Exception as exc:
        lines.append(StatusLine(recipe_id, "error", str(exc)))

    if not lines:
        lines.append(StatusLine(recipe_id, "ok", "complete"))
    return lines


def full_status(paths: RepoPaths | None = None) -> list[StatusLine]:
    paths = paths or RepoPaths()
    results: list[StatusLine] = []
    for recipe_id in paths.list_recipe_ids():
        results.extend(recipe_status(recipe_id, paths))
    if not paths.list_recipe_ids():
        results.append(StatusLine("-", "info", "no recipes yet"))
    return results


def pending_extractions(paths: RepoPaths | None = None) -> list[str]:
    """Recipe IDs in originals/ that lack YAML (heuristic for bulk migration)."""
    paths = paths or RepoPaths()
    existing = set(paths.list_recipe_ids())
    pending: list[str] = []
    for p in sorted(paths.originals.glob("*")):
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".pdf", ".txt", ".webp"}:
            stem = p.stem.split(".")[0] if p.name.startswith("PXL_") else p.stem
            if stem not in existing and p.name not in {x for x in existing}:
                pending.append(p.name)
    return pending
