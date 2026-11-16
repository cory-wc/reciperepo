"""Recipe id checks. A slug cannot choose a path outside recipes/."""

from __future__ import annotations

import re

RECIPE_ID_RE = re.compile(r"^wc-kitchen\.[a-z0-9]+(?:-[a-z0-9]+)*$")


class RecipeIdError(ValueError):
    """The recipe id is empty or contains characters that could change the path."""


def validate_recipe_id(recipe_id: str) -> str:
    if not RECIPE_ID_RE.fullmatch(recipe_id or ""):
        raise RecipeIdError(
            "recipe id must look like wc-kitchen.short-name "
            "(lowercase letters, numbers, and hyphens)"
        )
    return recipe_id


def slug_from_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise RecipeIdError(f"could not make a recipe id from {title!r}")
    return validate_recipe_id(f"wc-kitchen.{slug}")
