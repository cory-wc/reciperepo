from __future__ import annotations

import re
from pathlib import Path

NAMESPACE = "wc-kitchen"
DATE_SUFFIX_RE = re.compile(r"-\d{8}$")


def name_to_slug(name: str) -> str:
    """Convert recipe_name to kebab-case slug (see notes.md)."""
    name = re.sub(r"\(.*?\)", "", name)
    name = name.replace("&", "and")
    name = re.sub(r"[''\"']", "", name)
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def recipe_id_from_name(name: str, namespace: str = NAMESPACE) -> str:
    return f"{namespace}.{name_to_slug(name)}"


def recipe_id_from_source(source: Path, namespace: str = NAMESPACE) -> str:
    stem = source.stem.lower().replace("_", "-")
    stem = DATE_SUFFIX_RE.sub("", stem)
    return f"{namespace}.{stem}"


def next_available_recipe_id(base_id: str, paths, *, force: bool = False) -> str:
    """Return base_id, or base_id-2, base_id-3, ... when the target YAML exists."""
    if force or not paths.recipe_yaml(base_id).exists():
        return base_id

    n = 2
    while True:
        candidate = f"{base_id}-{n}"
        if not paths.recipe_yaml(candidate).exists():
            return candidate
        n += 1


def resolve_recipe_id(
    data: dict,
    paths,
    *,
    explicit_id: str | None = None,
    source: Path | None = None,
    force: bool = False,
) -> str:
    name = (data.get("recipe_name") or "").strip()
    if name:
        base_id = recipe_id_from_name(name)
    elif explicit_id:
        base_id = explicit_id
    elif source:
        base_id = recipe_id_from_source(source)
    else:
        raise ValueError("Cannot determine recipe id: no recipe_name, recipe_id, or source")

    return next_available_recipe_id(base_id, paths, force=force)
