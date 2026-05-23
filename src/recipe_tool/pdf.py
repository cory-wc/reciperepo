from __future__ import annotations

from pathlib import Path

from .paths import RepoPaths
from .render import render_recipe_html, get_jinja_env


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    file_url = html_path.resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="Letter",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()


def generate_recipe_pdf(recipe_id: str, paths: RepoPaths | None = None) -> Path:
    paths = paths or RepoPaths()
    paths.build.mkdir(parents=True, exist_ok=True)
    html_path = paths.build / f"{recipe_id}.print.html"
    render_recipe_html(recipe_id, paths, mode="print", output_path=html_path)
    pdf_path = paths.recipe_pdf(recipe_id)
    html_to_pdf(html_path, pdf_path)
    return pdf_path


def generate_index_pdf(paths: RepoPaths | None = None) -> Path:
    paths = paths or RepoPaths()
    from .index import build_index, render_index_html

    build_index(paths, allow_missing=True)
    html_path = paths.build / "index.print.html"
    render_index_html(paths, mode="print", output_path=html_path)
    pdf_path = paths.index_pdf()
    html_to_pdf(html_path, pdf_path)
    return pdf_path


def generate_all_pdfs(paths: RepoPaths | None = None) -> list[Path]:
    paths = paths or RepoPaths()
    results = [generate_recipe_pdf(rid, paths) for rid in paths.list_recipe_ids()]
    if paths.list_recipe_ids():
        results.append(generate_index_pdf(paths))
    return results
