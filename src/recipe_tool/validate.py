from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from schema.orf_models import Recipe, parse_recipe_yaml  # noqa: E402

from .load import load_recipe
from .paths import RepoPaths


def validate_recipe_id(recipe_id: str, paths: RepoPaths | None = None) -> Recipe:
    recipe, raw_data, yaml_path = load_recipe(recipe_id, paths)
    _validate_extensions(raw_data)
    _validate_source_reference(raw_data, paths or RepoPaths(), yaml_path)
    return recipe


def validate_all(paths: RepoPaths | None = None) -> list[str]:
    paths = paths or RepoPaths()
    errors: list[str] = []
    for recipe_id in paths.list_recipe_ids():
        try:
            validate_recipe_id(recipe_id, paths)
        except Exception as exc:
            errors.append(f"{recipe_id}: {exc}")
    return errors


def _validate_extensions(data: dict[str, Any]) -> None:
    for key in data:
        if key.startswith("X-") or key.startswith("x-"):
            if not key.startswith("X-"):
                raise ValueError(f"extension fields must use X-* pattern, got {key!r}")


def _validate_source_reference(
    data: dict[str, Any], paths: RepoPaths, yaml_path: Path
) -> None:
    if data.get("source_url"):
        return
    source = data.get("X-original-source")
    if not source:
        return
    source_path = (yaml_path.parent / source).resolve()
    if not source_path.exists():
        raise ValueError(f"X-original-source not found: {source}")


def parse_yaml_text(text: str) -> Recipe:
    return parse_recipe_yaml(text)
