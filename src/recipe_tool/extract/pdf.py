from __future__ import annotations

from pathlib import Path

import fitz


def extract_pdf_text(path: Path) -> str:
    doc = fitz.open(path)
    parts = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return "\n".join(parts).strip()


def extract_from_pdf(path: Path, recipe_id: str, repo_root, use_vision: bool = False) -> dict:
    text = extract_pdf_text(path)
    if len(text.strip()) < 80 and use_vision:
        from .vision import extract_from_image

        return extract_from_image(path, recipe_id, repo_root)

    from .llm import load_env, strip_yaml_fence, structure_text_to_yaml
    import yaml

    load_env(repo_root)
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
        {"status": "needs-review", "notes": ["Auto-extracted from PDF text"]},
    )
    return result
