from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    ingredients: list[dict[str, IngredientDetail]]
    steps: list[StepItem]
    notes: list[str] | str | None = None
    source_url: str | None = None
    source_authors: list[str] | None = None

    @field_validator("yields", mode="before")
    @classmethod
    def coerce_yields(cls, v: Any) -> Any:
        return v if v is not None else []

    @field_validator("ingredients", mode="before")
    @classmethod
    def validate_ingredients(cls, value: list[Any]) -> list[dict[str, IngredientDetail]]:
        if not value:
            raise ValueError("ingredients must not be empty")
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
        if not parsed:
            raise ValueError("ingredients must not be empty after filtering")
        return parsed

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_ingredient_field(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for item in data.get("ingredients") or []:
                if isinstance(item, dict) and "ingredient" in item:
                    raise ValueError(
                        "non-ORF 'ingredient:' field detected; use dict-key form (- sugar:)"
                    )
        return data


def parse_recipe_yaml(text: str) -> Recipe:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("recipe YAML must be a mapping")
    return Recipe.model_validate(data)


def recipe_to_dict(recipe: Recipe) -> dict[str, Any]:
    return recipe.model_dump(exclude_none=True, by_alias=False)
