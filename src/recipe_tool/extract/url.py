"""Fetch a public recipe page and map it to ORF without a model."""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import extruct
import httpx
from w3lib.html import get_base_url

from ..taxonomy import apply_taxonomy
from .ingredients import parse_ingredient_line

MAX_BYTES = 2_000_000
_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.google.com",
}
_NUTRITION_KEYS = {
    "calories": "calories",
    "carbohydratecontent": "carbohydrates",
    "proteincontent": "protein",
    "fatcontent": "fat",
    "fibercontent": "fiber",
    "sodiumcontent": "sodium",
    "sugarcontent": "sugar",
    "carbohydrates": "carbohydrates",
    "protein": "protein",
    "fat": "fat",
    "fiber": "fiber",
    "sodium": "sodium",
    "sugar": "sugar",
}


class RecipeFetchError(ValueError):
    """The URL is not a public http(s) page we can safely fetch."""


def assert_public_url(url: str) -> None:
    """Refuse non-http URLs and hosts that resolve to a local or metadata address."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RecipeFetchError(f"URL must be http or https: {url}")
    host = parsed.hostname.strip("[]").lower()
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".localhost"):
        raise RecipeFetchError(f"URL host is not allowed: {host}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RecipeFetchError(f"Could not resolve {host}") from exc
    if not infos:
        raise RecipeFetchError(f"Could not resolve {host}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or not ip.is_global
        ):
            raise RecipeFetchError(f"URL resolves to a non-public address: {ip}")


def fetch_url(url: str) -> tuple[str, str]:
    """GET a public page, re-checking every redirect, and return HTML and the final URL."""
    current = url
    assert_public_url(current)
    headers = {"User-Agent": "recipe-tool/0.1"}
    with httpx.Client(timeout=30.0, follow_redirects=False, headers=headers) as client:
        for _ in range(5):
            with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise RecipeFetchError("redirect missing location")
                    current = urljoin(str(resp.url), location)
                    assert_public_url(current)
                    continue
                resp.raise_for_status()
                length = resp.headers.get("content-length")
                if length and length.isdigit() and int(length) > MAX_BYTES:
                    raise RecipeFetchError("response exceeds 2 MB")
                chunks: list[bytes] = []
                size = 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise RecipeFetchError("response exceeds 2 MB")
                    chunks.append(chunk)
                body = b"".join(chunks)
                encoding = resp.encoding or "utf-8"
                return body.decode(encoding, errors="replace"), str(resp.url)
    raise RecipeFetchError("too many redirects")


def _fetch_browser(url: str) -> tuple[str, str]:
    assert_public_url(url)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            html = page.content()
            final = page.url
        finally:
            browser.close()
    if len(html.encode("utf-8")) > MAX_BYTES:
        raise RecipeFetchError("response exceeds 2 MB")
    assert_public_url(final)
    return html, final


def _strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("text")
                if name:
                    out.append(str(name))
            elif item:
                out.extend(_as_list(item) if not isinstance(item, str) else [str(item)])
        return [part for part in out if part]
    if isinstance(value, dict):
        name = value.get("name") or value.get("text")
        return [str(name)] if name else []
    return [str(value)]


def _recipe_nodes(html: str, page_url: str) -> list[dict[str, Any]]:
    base = get_base_url(html, page_url)
    extracted = extruct.extract(html, base_url=base, syntaxes=["json-ld", "microdata"])
    recipes: list[dict[str, Any]] = []

    def consider(node: Any) -> None:
        if not isinstance(node, dict):
            return
        kind = node.get("@type", "")
        kinds = kind if isinstance(kind, list) else [kind]
        if any(str(item) == "Recipe" or str(item).endswith("/Recipe") for item in kinds):
            recipes.append(node)
        graph = node.get("@graph")
        if isinstance(graph, list):
            for child in graph:
                consider(child)

    for item in extracted.get("json-ld", []):
        consider(item)
    return recipes


def format_duration(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _format_minutes(int(value))
    text = str(value).strip()
    if not text:
        return None
    if not text.startswith("P"):
        return text
    match = re.fullmatch(
        r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?",
        text,
    )
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, _seconds = (int(part) if part else 0 for part in match.groups())
    hours += days * 24
    return _format_minutes(hours * 60 + minutes)


def _format_minutes(total: int) -> str | None:
    if total <= 0:
        return None
    hours, minutes = divmod(total, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour" if hours == 1 else f"{hours} hours")
    if minutes:
        parts.append(f"{minutes} minute" if minutes == 1 else f"{minutes} minutes")
    return " ".join(parts) or None


def _authors(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, dict):
        name = value.get("name")
        return [str(name).strip()] if name else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_authors(item))
        return names
    return [str(value)]


def _yield_items(value: Any) -> tuple[list[dict[str, Any]], str | None]:
    if value is None or value == "":
        return [], None
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [{"amount": value, "unit": "servings"}], None
    text = _strip_tags(str(value))
    text = re.sub(r"^(makes|yields?)\s+", "", text, flags=re.IGNORECASE)
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(.*)$", text)
    if match:
        amount: str | int | float = match.group(1)
        amount = int(amount) if amount.isdigit() else float(amount)
        unit = match.group(2).strip() or "servings"
        return [{"amount": amount, "unit": unit}], None
    if text:
        return [{"amount": text, "unit": "servings"}], f"Yield was not split: {text}"
    return [], None


def _step_text(node: Any) -> str:
    if isinstance(node, str):
        return _strip_tags(node)
    if isinstance(node, dict):
        return _strip_tags(str(node.get("text") or node.get("name") or ""))
    return ""


def _steps_from_instructions(value: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, dict) and (
            item.get("@type") == "HowToSection" or "itemListElement" in item
        ):
            section = _strip_tags(str(item.get("name") or ""))
            for child in item.get("itemListElement") or []:
                text = _step_text(child)
                if not text:
                    continue
                step: dict[str, Any] = {"step": text}
                if section:
                    step["notes"] = [section]
                steps.append(step)
            continue
        text = _step_text(item)
        if text:
            steps.append({"step": text})
    return steps


def _nutrition(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for key, raw in value.items():
        mapped = _NUTRITION_KEYS.get(str(key).lower())
        if not mapped or raw in (None, ""):
            continue
        out[mapped] = raw
    return out


def _active_time(recipe: dict[str, Any]) -> str | None:
    for key, value in recipe.items():
        if re.search(r"active|hands[-_ ]?on", str(key), re.IGNORECASE):
            return format_duration(value)
    return None


def _scraper_record(html: str, page_url: str) -> dict[str, Any]:
    try:
        from recipe_scrapers import scrape_html
    except ImportError:
        return {}
    try:
        scraper = scrape_html(html, org_url=page_url, online=False)
    except TypeError:
        try:
            scraper = scrape_html(html, org_url=page_url)
        except Exception:
            return {}
    except Exception:
        return {}

    def call(name: str, default: Any = None) -> Any:
        method = getattr(scraper, name, None)
        if method is None:
            return default
        try:
            return method()
        except Exception:
            return default

    groups = call("ingredient_groups", []) or []
    grouped: list[tuple[str, list[str]]] = []
    for group in groups:
        purpose = str(getattr(group, "purpose", "") or "").strip()
        lines = [str(line).strip() for line in (getattr(group, "ingredients", []) or []) if str(line).strip()]
        if lines:
            grouped.append((purpose, lines))
    flat = [str(line).strip() for line in (call("ingredients", []) or []) if str(line).strip()]
    instructions = [str(line).strip() for line in (call("instructions_list", []) or []) if str(line).strip()]
    return {
        "title": call("title"),
        "author": call("author"),
        "description": call("description"),
        "yields": call("yields"),
        "prep": call("prep_time"),
        "cook": call("cook_time"),
        "total": call("total_time"),
        "cuisine": call("cuisine"),
        "category": call("category"),
        "nutrients": call("nutrients", {}) or {},
        "groups": grouped,
        "ingredients": flat,
        "instructions": instructions,
    }


def _ingredient_entries(lines: list[str], groups: list[tuple[str, list[str]]]) -> tuple[list[Any], list[str]]:
    source = []
    if groups:
        for purpose, group_lines in groups:
            if purpose:
                source.append(f"{purpose}:")
            source.extend(group_lines)
    else:
        source = lines
    entries: list[Any] = []
    notes: list[str] = []
    for line in source:
        entry, note = parse_ingredient_line(line)
        if entry is None:
            continue
        entries.append(entry)
        if note:
            notes.append(note)
    return entries, notes


def build_recipe(html: str, final_url: str, recipe_id: str | None = None) -> dict[str, Any]:
    """Map fetched HTML into an ORF dict. source_url is final_url, never a page link."""
    from ..ids import slug_from_title, validate_recipe_id

    assert_public_url(final_url)
    nodes = _recipe_nodes(html, final_url)
    schema = nodes[0] if nodes else {}
    scraped = _scraper_record(html, final_url)

    name = _strip_tags(str(schema.get("name") or scraped.get("title") or ""))
    if recipe_id:
        recipe_id = validate_recipe_id(recipe_id)
    elif name:
        recipe_id = slug_from_title(name)
    else:
        raise RecipeFetchError("no recipe found; rerun with the browser option")
    authors = _authors(schema.get("author"))
    if not authors and scraped.get("author"):
        authors = _authors(scraped.get("author"))
    description = _strip_tags(str(schema.get("description") or scraped.get("description") or ""))
    description = description[:500]

    ingredient_lines = list(scraped.get("ingredients") or [])
    groups = list(scraped.get("groups") or [])
    if not ingredient_lines and not groups:
        ingredient_lines = [
            _strip_tags(line) for line in _as_list(schema.get("recipeIngredient")) if _strip_tags(line)
        ]
    ingredients, unparsed = _ingredient_entries(ingredient_lines, groups)

    steps = [{"step": _strip_tags(line)} for line in scraped.get("instructions") or [] if _strip_tags(line)]
    if not steps:
        steps = _steps_from_instructions(schema.get("recipeInstructions"))

    yields, yield_note = _yield_items(schema.get("recipeYield") if schema.get("recipeYield") is not None else scraped.get("yields"))
    if not yields and scraped.get("yields") and schema.get("recipeYield") is not None:
        yields, yield_note = _yield_items(scraped.get("yields"))

    data: dict[str, Any] = {
        "recipe_uuid": recipe_id,
        "recipe_name": name,
        "source_url": final_url,
        "ingredients": ingredients,
        "steps": steps,
    }
    if authors:
        data["source_authors"] = authors
    if description:
        data["description"] = description
    if yields:
        data["yields"] = yields
    for field, raw in (
        ("X-prep_time", schema.get("prepTime") or scraped.get("prep")),
        ("X-cook_time", schema.get("cookTime") or scraped.get("cook")),
        ("X-total_time", schema.get("totalTime") or scraped.get("total")),
    ):
        formatted = format_duration(raw)
        if formatted:
            data[field] = formatted
    active = _active_time(schema)
    if active:
        data["X-active_time"] = active
    nutrition = _nutrition(schema.get("nutrition")) or _nutrition(scraped.get("nutrients"))
    if nutrition:
        data["X-nutrition"] = nutrition

    categories = _as_list(schema.get("recipeCategory"))
    if scraped.get("category"):
        categories = _unique_keep(categories + _as_list(scraped.get("category")))
    keywords = _as_list(schema.get("keywords"))
    cuisines = _as_list(schema.get("recipeCuisine"))
    if scraped.get("cuisine"):
        cuisines = _unique_keep(cuisines + _as_list(scraped.get("cuisine")))
    apply_taxonomy(data, categories=categories, keywords=keywords, cuisines=cuisines)

    notes = list(unparsed)
    if yield_note:
        notes.append(yield_note)
    cats = data.get("X-categories") or {}
    if "dish_type" not in cats:
        notes.append("dish_type was left empty")
    if "meal_type" not in cats:
        notes.append("meal_type was left empty")
    data["X-source-verification"] = {"status": "needs-review", "notes": notes}
    return data


def _unique_keep(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def page_to_recipe(
    html: str,
    final_url: str,
    recipe_id: str | None = None,
    *,
    use_browser_url: str | None = None,
) -> dict[str, Any]:
    data = build_recipe(html, final_url, recipe_id)
    if data["ingredients"] and data["steps"]:
        return data
    if use_browser_url:
        browser_html, browser_url = _fetch_browser(use_browser_url)
        data = build_recipe(browser_html, browser_url, recipe_id)
    if not data["ingredients"] and not data["steps"]:
        raise RecipeFetchError("no recipe found; rerun with the browser option")
    return data


def extract_from_url(
    url: str,
    recipe_id: str | None,
    repo_root,
    use_browser: bool = False,
) -> dict[str, Any]:
    del repo_root
    html, final_url = fetch_url(url)
    return page_to_recipe(
        html,
        final_url,
        recipe_id,
        use_browser_url=url if use_browser else None,
    )
