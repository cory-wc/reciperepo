from __future__ import annotations

from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _recipe_flags(data: dict[str, Any]) -> list[str]:
    flags = data.get("X-flags") or []
    if isinstance(flags, str):
        return [flags]
    return list(flags)


def is_reference_entry(data: dict[str, Any]) -> bool:
    return "index-page-not-a-recipe" in _recipe_flags(data)


def _coerce_note_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if len(item) != 1:
            raise ValueError("each note entry must be a string or single-key dict")
        key, val = next(iter(item.items()))
        return f"{key}: {val}"
    raise ValueError(f"invalid note entry: {item!r}")


class Amount(BaseModel):
    model_config = ConfigDict(extra="ignore")

    amount: str | int | float | None = None
    unit: str | None = None


class IngredientDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    amounts: list[Amount]
    processing: list[str] | None = None
    notes: list[str] | str | None = None


class StepItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    step: str
    notes: list[str] | None = None


class YieldItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    amount: str | int | float | None = None
    unit: str | None = None


class SourceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "needs-review"
    last_checked: str | None = None
    notes: list[str] = Field(default_factory=list)


class Recipe(BaseModel):
    model_config = ConfigDict(extra="allow")

    recipe_name: str
    recipe_uuid: str
    yields: list[YieldItem] = Field(default_factory=list)
    ingredients: list[dict[str, IngredientDetail]] = Field(default_factory=list)
    steps: list[StepItem] = Field(default_factory=list)
    notes: list[str] | str | None = None
    source_url: str | None = None
    source_authors: list[str] | None = None

    @field_validator("yields", mode="before")
    @classmethod
    def coerce_yields(cls, v: Any) -> Any:
        return v if v is not None else []

    @field_validator("ingredients", mode="before")
    @classmethod
    def validate_ingredients(cls, value: Any) -> list[dict[str, IngredientDetail]]:
        if not value:
            return []
        parsed: list[dict[str, IngredientDetail]] = []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("each ingredient must be a dict")
            if "ingredient" in item:
                raise ValueError(
                    "non-ORF 'ingredient:' field detected; use dict-key form (- sugar:)"
                )
            if len(item) != 1:
                raise ValueError("each ingredient entry must have exactly one key (the name)")
            name, detail = next(iter(item.items()))
            if not name.strip():
                raise ValueError("ingredient name must not be empty")
            # Skip group-header entries where the value is a plain string
            # (e.g. "X-group: Veggies", "heading: Sauce", "note: choose one:")
            if isinstance(detail, str):
                continue
            if isinstance(detail, IngredientDetail):
                parsed.append({name: detail})
            else:
                parsed.append({name: IngredientDetail.model_validate(detail)})
        return parsed

    @model_validator(mode="before")
    @classmethod
    def prepare_recipe_data(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for item in data.get("ingredients") or []:
            if isinstance(item, dict) and "ingredient" in item:
                raise ValueError(
                    "non-ORF 'ingredient:' field detected; use dict-key form (- sugar:)"
                )
        notes = data.get("notes")
        if notes is not None:
            if isinstance(notes, str):
                data["notes"] = [notes]
            elif isinstance(notes, list):
                data["notes"] = [_coerce_note_item(n) for n in notes]
        if is_reference_entry(data):
            data.setdefault("ingredients", [])
            data.setdefault("steps", [])
        return data

    @model_validator(mode="after")
    def require_recipe_body(self) -> Self:
        extras = self.__pydantic_extra__ or {}
        flags = extras.get("X-flags") or []
        if isinstance(flags, str):
            flags = [flags]
        if "index-page-not-a-recipe" in flags:
            return self
        if not self.ingredients:
            raise ValueError("ingredients must not be empty")
        if not self.steps:
            raise ValueError("steps must not be empty")
        return self


def parse_recipe_yaml(text: str) -> Recipe:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("recipe YAML must be a mapping")
    return Recipe.model_validate(data)


def recipe_to_dict(recipe: Recipe) -> dict[str, Any]:
    return recipe.model_dump(exclude_none=True, by_alias=False)
