"""Split an ingredient line into an ORF name, amount, and unit."""

from __future__ import annotations

import re
from typing import Any

_FRACTIONS = {
    "½": "1/2",
    "⅓": "1/3",
    "⅔": "2/3",
    "¼": "1/4",
    "¾": "3/4",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}

_UNITS = (
    "tablespoons",
    "tablespoon",
    "teaspoons",
    "teaspoon",
    "kilograms",
    "kilogram",
    "milliliters",
    "milliliter",
    "ounces",
    "ounce",
    "pounds",
    "pound",
    "cloves",
    "clove",
    "pinches",
    "pinch",
    "cups",
    "cup",
    "tbsp",
    "tbs",
    "tsp",
    "grams",
    "gram",
    "kg",
    "ml",
    "oz",
    "lbs",
    "lb",
    "cans",
    "can",
    "liters",
    "liter",
    "whole",
    "g",
    "l",
)

_PROCESSING = {
    "chopped",
    "diced",
    "minced",
    "sliced",
    "grated",
    "shredded",
    "crushed",
    "peeled",
    "trimmed",
    "halved",
    "quartered",
    "melted",
    "softened",
    "divided",
    "packed",
    "sifted",
    "toasted",
    "rinsed",
    "drained",
    "thawed",
    "defrosted",
    "beaten",
    "julienned",
}

_NOTE_PHRASES = ("to taste", "for serving", "as needed")

_QTY = re.compile(
    r"^(?P<qty>(?:\d+\s+)?\d+\s*/\s*\d+|\d+\s+\d+\s*/\s*\d+|\d+(?:\.\d+)?)"
)
_UNIT = re.compile(
    r"^(?P<unit>" + "|".join(re.escape(unit) for unit in _UNITS) + r")\b\.?\s*",
    re.IGNORECASE,
)


def _normalize_fractions(text: str) -> str:
    for glyph, ascii_frac in _FRACTIONS.items():
        text = re.sub(rf"(\d)\s*{glyph}", rf"\1 {ascii_frac}", text)
        text = text.replace(glyph, ascii_frac)
    return text


def _amount(token: str) -> str | int | float:
    token = re.sub(r"\s*/\s*", "/", token.strip())
    mixed = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", token)
    if mixed:
        whole, num, den = (int(part) for part in mixed.groups())
        if den == 0:
            return token
        value = whole + num / den
        return int(value) if value.is_integer() else value
    fraction = re.fullmatch(r"(\d+)/(\d+)", token)
    if fraction:
        num, den = (int(part) for part in fraction.groups())
        if den == 0:
            return token
        value = num / den
        return int(value) if value.is_integer() else value
    if re.fullmatch(r"\d+", token):
        return int(token)
    return float(token)


def _split_tail(name: str) -> tuple[str, list[str], list[str]]:
    if "," not in name:
        return name.strip(), [], []
    head, tail = name.split(",", 1)
    tail = tail.strip(" .")
    words = {word.strip(" .").lower() for word in re.split(r"\s+", tail) if word}
    if words and words <= _PROCESSING:
        return head.strip(), [tail], []
    return head.strip(), [], [tail] if tail else []


def parse_ingredient_line(line: str) -> tuple[Any, str | None]:
    """Return an ORF ingredient entry, or a group header, plus an optional note.

    A group header is a one-key dict whose value is a string. A parsed ingredient
    is a one-key dict of name to amounts. When the line cannot be split, the
    name is the whole line and the note explains that.
    """
    text = _normalize_fractions(re.sub(r"\s+", " ", line).strip(" \t•-*"))
    if not text:
        return None, None
    if not _QTY.match(text) and len(text) <= 40 and text.endswith(":"):
        header = text[:-1].strip() or text
        return {header: header}, None

    lowered = text.lower()
    for phrase in _NOTE_PHRASES:
        if phrase in lowered and not _QTY.match(text):
            name = re.sub(re.escape(phrase), "", text, count=1, flags=re.IGNORECASE)
            name = name.strip(" ,.;")
            detail: dict[str, Any] = {"amounts": []}
            detail["notes"] = [phrase]
            return {name or text: detail}, None

    match = _QTY.match(text)
    if not match:
        return {text: {"amounts": []}}, f"Ingredient line was not split: {text}"

    amount = _amount(match.group("qty"))
    rest = text[match.end() :].strip()
    unit = None
    unit_match = _UNIT.match(rest)
    if unit_match:
        unit = unit_match.group("unit").lower()
        rest = rest[unit_match.end() :].strip()
    if not rest:
        rest = text
    name, processing, notes = _split_tail(rest)
    detail = {"amounts": [{"amount": amount, "unit": unit}]}
    if processing:
        detail["processing"] = processing
    if notes:
        detail["notes"] = notes
    return {name: detail}, None
