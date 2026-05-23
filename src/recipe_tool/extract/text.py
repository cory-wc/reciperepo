from __future__ import annotations

from pathlib import Path

import yaml

from .llm import load_env, strip_yaml_fence, structure_text_to_yaml


def extract_from_text(path: Path, recipe_id: str, repo_root) -> dict:
    load_env(repo_root)
    text = path.read_text(encoding="utf-8")
    rel = f"../originals/{path.name}"
    yaml_text = strip_yaml_fence(
        structure_text_to_yaml(
            text,
            repo_root,
            extra=f"recipe_uuid: {recipe_id}\nX-original-source: {rel}",
        )
    )
    result = yaml.safe_load(yaml_text)
    result.setdefault("recipe_uuid", recipe_id)
    result.setdefault("X-original-source", rel)
    result.setdefault(
        "X-source-verification",
        {"status": "needs-review", "notes": ["Auto-extracted from text file"]},
    )
    return result
