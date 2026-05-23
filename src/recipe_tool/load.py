from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

# Allow imports from schema/ when running from repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from schema.orf_models import Recipe, parse_recipe_yaml, recipe_to_dict  # noqa: E402

from .paths import RepoPaths


def load_recipe(recipe_id: str, paths: RepoPaths | None = None) -> tuple[Recipe, dict[str, Any], Path]:
    paths = paths or RepoPaths()
    yaml_path = paths.recipe_yaml(recipe_id)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Recipe not found: {yaml_path}")
    raw = yaml_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    recipe = parse_recipe_yaml(raw)
    return recipe, data, yaml_path


def dump_recipe(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
