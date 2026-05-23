from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .load import load_recipe
from .paths import RepoPaths


def _format_amount(amount: str | int | float) -> str:
    if isinstance(amount, str):
        if "/" in amount:
            try:
                parts = amount.split("/")
                if len(parts) == 2:
                    value = float(Fraction(int(parts[0].strip()), int(parts[1].strip())))
                    return _format_decimal(value)
            except (ValueError, ZeroDivisionError):
                return amount
        try:
            return _format_decimal(float(amount))
        except ValueError:
            return amount
    if isinstance(amount, float):
        return _format_decimal(amount)
    return str(amount)


def _format_decimal(value: float) -> str:
    whole = int(value)
    frac = value - whole
    if abs(frac) < 1e-9:
        return str(whole)
    for denom in (2, 3, 4, 5, 8):
        num = round(frac * denom)
        if abs(frac - num / denom) < 0.02:
            if whole == 0:
                return f"{num}/{denom}"
            return f"{whole} {num}/{denom}"
    return f"{value:.2g}".rstrip("0").rstrip(".")


def _format_unit(unit: str, amount_display: str) -> str:
    unit_lower = unit.lower()
    if unit_lower == "cup" and amount_display in ("1/4", "¼"):
        return "¼ C"
    if unit_lower == "cup":
        return "C" if amount_display == "1" else f"{amount_display} C"
    if unit_lower == "tablespoons":
        return "tbsp"
    if unit_lower == "teaspoons":
        return "tsp"
    if unit_lower in ("lb", "pound", "pounds"):
        return "lb"
    return unit


def format_ingredient_row(name: str, detail: dict[str, Any]) -> dict[str, str]:
    amounts = detail.get("amounts") or [{}]
    first = amounts[0]
    amount_raw = first.get("amount", "")
    unit = first.get("unit", "")
    amount_display = _format_amount(amount_raw)

    if unit.lower() == "cup" and amount_display == "1/4":
        amount_str = "¼ C"
    elif unit.lower() == "cup":
        amount_str = "¼ C" if amount_display == "1/4" else (
            f"{amount_display} C" if amount_display != "1" else "1 C"
        )
    elif unit.lower() == "tablespoons":
        amount_str = f"{amount_display} tbsp".strip()
    elif unit.lower() in ("lb", "pound", "pounds"):
        amount_str = f"{amount_display} lb".strip()
    elif unit.lower() == "onions":
        amount_str = amount_display
    elif unit.lower() == "each":
        amount_str = amount_display
    else:
        amount_str = f"{amount_display} {unit}".strip()

    processing = detail.get("processing") or []
    name_lower = name.lower()
    if len(processing) >= 2:
        name_html = f"{name_lower}, {processing[0]} and<br>{processing[1]}"
    elif len(processing) == 1:
        proc = processing[0]
        if "inch" in proc or "cube" in proc:
            name_html = f"{name_lower},<br>{proc.replace('cut into ', '')}"
        else:
            name_html = f"{name_lower}, {proc}"
    else:
        name_html = name_lower

    return {"amount": amount_str, "name": name_html}


def build_meta_line(data: dict[str, Any]) -> str:
    parts: list[str] = []
    active = data.get("X-active_time")
    total = data.get("X-total_time")
    if active:
        parts.append(f"{active}".replace(" minutes", "m active").replace(" minute", "m active"))
    elif total:
        parts.append(f"{total}".replace(" minutes", "m").replace(" minute", "m"))

    yields = data.get("yields") or []
    if yields:
        y = yields[0]
        amt = y.get("amount", "")
        unit = y.get("unit", "servings")
        parts.append(f"serves {amt}")

    nutrition = data.get("X-nutrition") or {}
    if nutrition.get("calories"):
        parts.append(f"{nutrition['calories']} calories")
    if nutrition.get("fiber"):
        fiber = str(nutrition["fiber"]).replace(" ", "")
        if not fiber.endswith("g"):
            fiber = f"{fiber}g"
        parts.append(f"{fiber} fiber")

    return " • ".join(parts)


def recipe_context(recipe_id: str, paths: RepoPaths | None = None) -> dict[str, Any]:
    _, data, _ = load_recipe(recipe_id, paths)
    ingredients = []
    for item in data.get("ingredients") or []:
        name, detail = next(iter(item.items()))
        ingredients.append(format_ingredient_row(name, detail))

    steps = []
    for i, step_item in enumerate(data.get("steps") or [], start=1):
        text = step_item.get("step", "")
        text = re.sub(r"\s+", " ", text.strip())
        text = text.replace("about 10 minutes", "~10 minutes")
        text = text.replace("a stock pot", "stock pot")
        text = text.replace("a boil", "boil")
        steps.append({"num": i, "text": text})

    return {
        "recipe_id": recipe_id,
        "title": data.get("recipe_name", recipe_id),
        "meta": build_meta_line(data),
        "ingredients": ingredients,
        "steps": steps,
        "source_url": data.get("source_url"),
    }


def get_jinja_env(paths: RepoPaths) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(paths.templates)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_recipe_html(
    recipe_id: str,
    paths: RepoPaths | None = None,
    mode: str = "screen",
    output_path: Path | None = None,
) -> str:
    paths = paths or RepoPaths()
    env = get_jinja_env(paths)
    template = env.get_template("recipe.html.j2")
    html = template.render(**recipe_context(recipe_id, paths), mode=mode)
    dest = output_path or paths.recipe_html(recipe_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return html


def render_all_recipes(paths: RepoPaths | None = None, mode: str = "screen") -> list[str]:
    paths = paths or RepoPaths()
    rendered = []
    for recipe_id in paths.list_recipe_ids():
        render_recipe_html(recipe_id, paths, mode=mode)
        rendered.append(recipe_id)
    return rendered
