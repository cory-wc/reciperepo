"""Local table UI for reviewing and editing recipe metadata."""

from __future__ import annotations

import json
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .load import dump_recipe, load_recipe
from .metadata_facets import (
    CATEGORY_FACET_KEYS,
    FACET_KEYS,
    FACET_LABELS,
    TAG_FACET_KEYS,
    extract_facets,
    is_filterable_metadata,
    metadata_cleanup_issues,
    norm_token,
)
from .paths import RepoPaths
from .validate import validate_recipe_id

_TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "metadata-editor.html"

_FACET_COLUMNS = [
    {"key": k, "label": FACET_LABELS[k], "group": "categories"}
    for k in CATEGORY_FACET_KEYS
] + [
    {"key": k, "label": FACET_LABELS[k], "group": "tags"} for k in TAG_FACET_KEYS
]


def _parse_csv(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[,;]", raw)
    return [norm_token(p) for p in parts if p.strip()]


def _join_values(values: list[str] | None) -> str:
    if not values:
        return ""
    return ", ".join(values)


def _legacy_summary(data: dict[str, Any]) -> str:
    parts: list[str] = []
    if data.get("X-category") is not None:
        parts.append(f"X-category: {data.get('X-category')}")
    if data.get("X-dietary") is not None:
        parts.append(f"X-dietary: {data.get('X-dietary')}")
    if data.get("X-cuisine") is not None:
        parts.append(f"X-cuisine: {data.get('X-cuisine')}")
    tags = data.get("X-tags")
    if isinstance(tags, list):
        parts.append(f"X-tags: {tags}")
    return " · ".join(parts)


def recipe_to_row(recipe_id: str, data: dict[str, Any]) -> dict[str, Any]:
    facets = extract_facets(data)
    issues = metadata_cleanup_issues(data)
    return {
        "id": recipe_id,
        "name": data.get("recipe_name", recipe_id),
        "filterable": is_filterable_metadata(data),
        "issues": issues,
        "legacy": _legacy_summary(data),
        "fields": {key: _join_values(facets.get(key)) for key in FACET_KEYS},
    }


def list_recipe_rows(paths: RepoPaths | None = None) -> list[dict[str, Any]]:
    paths = paths or RepoPaths()
    rows = []
    for recipe_id in paths.list_recipe_ids():
        _, data, _ = load_recipe(recipe_id, paths)
        rows.append(recipe_to_row(recipe_id, data))
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def apply_metadata_update(
    recipe_id: str,
    fields: dict[str, str],
    paths: RepoPaths | None = None,
) -> dict[str, Any]:
    paths = paths or RepoPaths()
    _, data, yaml_path = load_recipe(recipe_id, paths)

    categories: dict[str, list[str]] = {}
    for key in CATEGORY_FACET_KEYS:
        values = _parse_csv(fields.get(key, ""))
        if values:
            categories[key] = values

    tags: dict[str, list[str]] = {}
    for key in TAG_FACET_KEYS:
        values = _parse_csv(fields.get(key, ""))
        if values:
            tags[key] = values

    if categories:
        data["X-categories"] = categories
    else:
        data.pop("X-categories", None)

    if tags:
        data["X-tags"] = tags
    else:
        data.pop("X-tags", None)

    for legacy_key in ("X-category", "X-dietary", "X-cuisine"):
        data.pop(legacy_key, None)

    dump_recipe(data, yaml_path)
    validate_recipe_id(recipe_id, paths)
    return recipe_to_row(recipe_id, data)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_response(handler: BaseHTTPRequestHandler, html: str) -> None:
    body = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def create_handler(paths: RepoPaths, columns: list[dict[str, str]]):
    template_html = _TEMPLATE.read_text(encoding="utf-8")
    config_json = json.dumps({"columns": columns}, ensure_ascii=False)

    class MetadataEditorHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            if args and str(args[0]).startswith("GET /api"):
                return
            super().log_message(format, *args)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path in ("/", "/index.html"):
                html = template_html.replace("__CONFIG__", config_json)
                _html_response(self, html)
                return

            if path == "/api/recipes":
                _json_response(self, 200, {"recipes": list_recipe_rows(paths)})
                return

            self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            match = re.fullmatch(r"/api/recipes/([^/]+)", parsed.path)
            if not match:
                self.send_error(404)
                return

            recipe_id = unquote(match.group(1))
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                _json_response(self, 400, {"error": "invalid JSON"})
                return

            fields = payload.get("fields")
            if not isinstance(fields, dict):
                _json_response(self, 400, {"error": "fields object required"})
                return

            try:
                row = apply_metadata_update(recipe_id, fields, paths)
            except FileNotFoundError:
                _json_response(self, 404, {"error": f"recipe not found: {recipe_id}"})
                return
            except Exception as exc:
                _json_response(self, 400, {"error": str(exc)})
                return

            _json_response(self, 200, {"recipe": row})

    return MetadataEditorHandler


def run_metadata_editor(
    paths: RepoPaths | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    paths = paths or RepoPaths()
    handler = create_handler(paths, _FACET_COLUMNS)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"

    print(f"Metadata editor at {url}")
    print("Edit comma-separated values; Save writes X-categories / X-tags to recipe YAML.")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
