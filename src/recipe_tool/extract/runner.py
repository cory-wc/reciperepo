from __future__ import annotations

from pathlib import Path

from ..load import dump_recipe
from ..paths import RepoPaths
from ..validate import parse_yaml_text
from .pdf import extract_from_pdf
from .text import extract_from_text
from .url import extract_from_url
from .vision import extract_from_image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
TEXT_SUFFIXES = {".txt", ".md"}
PDF_SUFFIXES = {".pdf"}


def run_extract(
    recipe_id: str | None,
    url: str | None,
    source: Path | None,
    paths: RepoPaths | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> Path | None:
    paths = paths or RepoPaths()
    if not recipe_id:
        raise ValueError("recipe_id is required unless using --pending")

    out_path = paths.recipe_yaml(recipe_id)
    if out_path.exists() and not force:
        raise FileExistsError(f"{out_path} exists; use --force to overwrite")

    if url:
        data = extract_from_url(url, recipe_id, paths.root)
    elif source:
        source = source if source.is_absolute() else paths.root / source
        if not source.exists():
            raise FileNotFoundError(source)
        suffix = source.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            data = extract_from_image(source, recipe_id, paths.root)
        elif suffix in PDF_SUFFIXES:
            data = extract_from_pdf(source, recipe_id, paths.root, use_vision=True)
        elif suffix in TEXT_SUFFIXES:
            data = extract_from_text(source, recipe_id, paths.root)
        else:
            raise ValueError(f"Unsupported source type: {suffix}")
    else:
        raise ValueError("Provide --url or --source")

    import yaml
    from schema.orf_models import parse_recipe_yaml

    yaml_text = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    parse_recipe_yaml(yaml_text)

    if dry_run:
        print(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))
        return None

    dump_recipe(data, out_path)
    return out_path


def run_extract_pending(paths: RepoPaths | None = None, dry_run: bool = False) -> list[str]:
    paths = paths or RepoPaths()
    processed = []
    for p in sorted(paths.originals.glob("*")):
        if p.suffix.lower() not in IMAGE_SUFFIXES | PDF_SUFFIXES | TEXT_SUFFIXES:
            continue
        # Heuristic: skip if any yaml already references this file
        referenced = False
        for ypath in paths.recipes.glob("*.yaml"):
            if ypath.name == "index.yaml":
                continue
            if p.name in ypath.read_text(encoding="utf-8"):
                referenced = True
                break
        if referenced:
            continue
        recipe_id = p.stem.lower().replace("_", "-")
        if not recipe_id.startswith("wc-kitchen."):
            recipe_id = f"wc-kitchen.{recipe_id}"
        try:
            run_extract(recipe_id, None, p, paths, dry_run=dry_run, force=False)
            processed.append(recipe_id)
        except FileExistsError:
            continue
        except Exception as exc:
            print(f"Skip {p.name}: {exc}")
    return processed
