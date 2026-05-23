from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from .load import load_recipe
from .paths import RepoPaths


def _parse_amount(amount: str | int | float) -> float | None:
    if isinstance(amount, (int, float)):
        return float(amount)
    text = str(amount).strip()
    if "/" in text:
        try:
            num, den = text.split("/", 1)
            return float(Fraction(int(num.strip()), int(den.strip())))
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(text)
    except ValueError:
        return None


def collect_ingredients(recipe_ids: list[str], paths: RepoPaths | None = None) -> list[dict[str, Any]]:
    paths = paths or RepoPaths()
    items: list[dict[str, Any]] = []
    for recipe_id in recipe_ids:
        _, data, _ = load_recipe(recipe_id, paths)
        for ing in data.get("ingredients") or []:
            name, detail = next(iter(ing.items()))
            for amt in detail.get("amounts") or []:
                items.append(
                    {
                        "recipe_id": recipe_id,
                        "name": name,
                        "amount": amt.get("amount"),
                        "unit": (amt.get("unit") or "").lower(),
                        "processing": detail.get("processing") or [],
                    }
                )
    return items


def merge_shopping_list(recipe_ids: list[str], paths: RepoPaths | None = None) -> tuple[list[str], list[str]]:
    paths = paths or RepoPaths()
    items = collect_ingredients(recipe_ids, paths)
    merged: dict[tuple[str, str], float] = defaultdict(float)
    conflicts: list[str] = []
    unmergeable: list[str] = []

    for item in items:
        name = item["name"].lower()
        unit = item["unit"]
        value = _parse_amount(item["amount"])
        key = (name, unit)
        if value is None:
            unmergeable.append(f"{item['amount']} {unit} {item['name']} (from {item['recipe_id']})")
            continue
        if key in merged and merged[key] != value:
            conflicts.append(
                f"Conflict for {item['name']} ({unit}): existing {merged[key]} vs {value} from {item['recipe_id']}"
            )
        merged[key] += value

    lines = []
    for (name, unit), total in sorted(merged.items()):
        if total == int(total):
            display = str(int(total))
        else:
            display = str(total)
        lines.append(f"- {display} {unit} {name}".strip())

    lines.extend(unmergeable)
    return lines, conflicts


def format_shopping_list(recipe_ids: list[str], paths: RepoPaths | None = None) -> str:
    lines, conflicts = merge_shopping_list(recipe_ids, paths)
    header = f"# Shopping list ({len(recipe_ids)} recipes)\n"
    body = "\n".join(lines) if lines else "(no mergeable ingredients)"
    out = header + "\n" + body
    if conflicts:
        out += "\n\n## Conflicts (review manually)\n" + "\n".join(f"- {c}" for c in conflicts)
    return out + "\n"
