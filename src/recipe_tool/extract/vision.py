from __future__ import annotations

from pathlib import Path

import yaml

from .llm import image_to_yaml, load_env, strip_yaml_fence


def extract_from_image(path: Path, recipe_id: str, repo_root) -> dict:
    load_env(repo_root)
    yaml_text = strip_yaml_fence(image_to_yaml(path, repo_root, recipe_id))
    result = yaml.safe_load(yaml_text)
    result.setdefault("recipe_uuid", recipe_id)
    rel = f"../originals/{path.name}"
    result.setdefault("X-original-source", rel)
    result.setdefault(
        "X-source-verification",
        {"status": "needs-review", "notes": ["Auto-extracted from image via vision API"]},
    )
    return result
