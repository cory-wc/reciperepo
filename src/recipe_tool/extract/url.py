from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import extruct
import httpx
from w3lib.html import get_base_url


def fetch_url(url: str) -> tuple[str, str]:
    resp = httpx.get(url, follow_redirects=True, timeout=30.0, headers={"User-Agent": "recipe-tool/0.1"})
    resp.raise_for_status()
    return resp.text, str(resp.url)


def _first(lst: Any) -> Any:
    if isinstance(lst, list) and lst:
        return lst[0]
    return lst


def _parse_iso_duration(text: str | None) -> str | None:
    if not text or not text.startswith("PT"):
        return text
    # Simple PT30M -> 30 minutes
    import re

    m = re.search(r"(\d+)M", text)
    if m:
        return f"{m.group(1)} minutes"
    return text


def jsonld_to_orf(recipe: dict[str, Any], source_url: str, recipe_id: str) -> dict[str, Any]:
    name = recipe.get("name") or recipe_id
    ingredients_raw = recipe.get("recipeIngredient") or []
    instructions_raw = recipe.get("recipeInstructions") or []

    mapped_ingredients = []
    for line in ingredients_raw:
        text = line if isinstance(line, str) else line.get("text", str(line))
        mapped_ingredients.append({text: {"amounts": [{"amount": 1, "unit": "as listed"}]}})

    steps = []
    for inst in instructions_raw:
        if isinstance(inst, str):
            steps.append({"step": inst})
        elif isinstance(inst, dict):
            steps.append({"step": inst.get("text") or inst.get("name") or str(inst)})

    data: dict[str, Any] = {
        "recipe_uuid": recipe_id,
        "recipe_name": name,
        "source_url": source_url,
        "ingredients": mapped_ingredients,
        "steps": steps,
        "X-source-verification": {"status": "needs-review", "notes": ["Auto-extracted from URL JSON-LD"]},
    }

    yield_val = recipe.get("recipeYield")
    if yield_val:
        y = _first(yield_val) if isinstance(yield_val, list) else yield_val
        if isinstance(y, str):
            data["yields"] = [{"amount": y, "unit": "servings"}]
        elif isinstance(y, (int, float)):
            data["yields"] = [{"amount": y, "unit": "servings"}]

    if recipe.get("totalTime"):
        data["X-total_time"] = _parse_iso_duration(recipe.get("totalTime"))
    if recipe.get("author"):
        author = recipe["author"]
        if isinstance(author, dict):
            data["source_authors"] = [author.get("name", str(author))]
        elif isinstance(author, list):
            data["source_authors"] = [
                a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in author
            ]
        else:
            data["source_authors"] = [str(author)]

    return data


def extract_from_url(url: str, recipe_id: str, repo_root) -> dict[str, Any]:
    html, final_url = fetch_url(url)
    base = get_base_url(html, final_url)
    data = extruct.extract(html, base_url=base, syntaxes=["json-ld", "microdata"])
    recipes = []
    for item in data.get("json-ld", []):
        if isinstance(item, dict):
            if item.get("@type") == "Recipe" or "Recipe" in str(item.get("@type", "")):
                recipes.append(item)
            if "@graph" in item:
                for node in item["@graph"]:
                    if node.get("@type") == "Recipe" or "Recipe" in str(node.get("@type", "")):
                        recipes.append(node)
    if recipes:
        return jsonld_to_orf(recipes[0], final_url, recipe_id)

    from .llm import load_env, strip_yaml_fence, structure_text_to_yaml
    import yaml

    load_env(repo_root)
    text = httpx.get(final_url, follow_redirects=True).text
    # crude text extraction
    import re

    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain)
    yaml_text = strip_yaml_fence(
        structure_text_to_yaml(plain[:12000], repo_root, extra=f"source_url: {final_url}\nrecipe_uuid: {recipe_id}")
    )
    result = yaml.safe_load(yaml_text)
    result["source_url"] = final_url
    result.setdefault("recipe_uuid", recipe_id)
    result.setdefault(
        "X-source-verification",
        {"status": "needs-review", "notes": ["Auto-extracted from URL via LLM"]},
    )
    return result
