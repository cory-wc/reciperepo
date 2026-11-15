"""Add a recipe from a public URL, and promote a draft into the published set."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .extract.url import extract_from_url
from .ids import validate_recipe_id
from .index import generate_index
from .load import dump_recipe
from .paths import RepoPaths
from .pdf import generate_recipe_pdf
from .render import render_recipe_html
from .validate import validate_recipe_id as validate_recipe_yaml


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def run_add(
    url: str,
    paths: RepoPaths | None = None,
    *,
    published: bool = False,
    recipe_id: str | None = None,
    browser: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """Fetch a URL, write ORF YAML, and return the recipe id.

    Human messages go to stderr. Callers that need the id read the return value.
    """
    paths = paths or RepoPaths()
    if recipe_id:
        recipe_id = validate_recipe_id(recipe_id)
    data = extract_from_url(url, recipe_id, paths.root, use_browser=browser)
    recipe_id = validate_recipe_id(str(data["recipe_uuid"]))

    from schema.orf_models import parse_recipe_yaml

    yaml_text = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    parse_recipe_yaml(yaml_text)

    destination = paths.recipe_yaml(recipe_id) if published else paths.draft_yaml(recipe_id)
    if paths.recipe_id_taken(recipe_id) and not force:
        raise FileExistsError(f"{recipe_id} already exists; use --force to overwrite")
    if dry_run:
        sys.stdout.write(yaml_text)
        if not yaml_text.endswith("\n"):
            sys.stdout.write("\n")
        return recipe_id
    dump_recipe(data, destination)
    _eprint(f"Wrote {destination}")
    return recipe_id


def publish_recipe(recipe_id: str, paths: RepoPaths | None = None) -> Path:
    """Move a draft into recipes/ and rebuild its page, PDF, and the index."""
    paths = paths or RepoPaths()
    recipe_id = validate_recipe_id(recipe_id)
    source = paths.draft_yaml(recipe_id)
    destination = paths.recipe_yaml(recipe_id)
    if not source.exists():
        raise FileNotFoundError(f"No draft at {source}")
    if destination.exists():
        raise FileExistsError(f"{destination} already exists")

    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    original = data.get("X-original-source") if isinstance(data, dict) else None
    if isinstance(original, str) and original.startswith("../../originals/"):
        data["X-original-source"] = "../originals/" + original.removeprefix("../../originals/")
        dump_recipe(data, destination)
        source.unlink()
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)

    validate_recipe_yaml(recipe_id, paths)
    render_recipe_html(recipe_id, paths, mode="screen")
    generate_recipe_pdf(recipe_id, paths)
    generate_index(paths, allow_missing=True, include_pdf=True)
    _eprint(f"Published {destination}")
    return destination


def add_many(
    urls: list[str],
    paths: RepoPaths | None = None,
    *,
    recipe_id: str | None = None,
    browser: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Add each URL. Keep going after a failure. Return successes and failures."""
    paths = paths or RepoPaths()
    usable = [url.strip() for url in urls if url and url.strip()]
    if not usable:
        raise ValueError("at least one recipe URL is required")
    if len(usable) > 5:
        raise ValueError("at most five URLs per run")
    explicit_id = recipe_id if len(usable) == 1 else None
    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    for url in usable:
        try:
            recipe_id_out = run_add(
                url,
                paths,
                published=True,
                recipe_id=explicit_id,
                browser=browser,
            )
            successes.append({"url": url, "recipe_id": recipe_id_out})
        except Exception as exc:
            failures.append({"url": url, "error": str(exc)})
            _eprint(f"Failed {url}: {exc}")
    return successes, failures
