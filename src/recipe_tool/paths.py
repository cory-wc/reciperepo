from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "recipes").is_dir() and (candidate / "pyproject.toml").exists():
            return candidate
    if (current / "recipes").is_dir():
        return current
    raise FileNotFoundError("Could not find reciperepo root (need recipes/ and pyproject.toml)")


class RepoPaths:
    def __init__(self, root: Path | None = None) -> None:
        self.root = find_repo_root(root)
        self.recipes = self.root / "recipes"
        self.originals = self.root / "originals"
        self.pdfs = self.root / "pdfs"
        self.site = self.root / "site"
        self.templates = self.root / "templates"
        self.prompts = self.root / "prompts"
        self.build = self.root / "build"
        self.lists = self.root / "lists"

    def recipe_yaml(self, recipe_id: str) -> Path:
        return self.recipes / f"{recipe_id}.yaml"

    def recipe_pdf(self, recipe_id: str) -> Path:
        return self.pdfs / f"{recipe_id}.pdf"

    def recipe_html(self, recipe_id: str) -> Path:
        return self.site / f"{recipe_id}.html"

    def index_yaml(self) -> Path:
        return self.recipes / "index.yaml"

    def index_html(self) -> Path:
        return self.site / "index.html"

    def index_pdf(self) -> Path:
        return self.pdfs / "index.pdf"

    def list_recipe_ids(self) -> list[str]:
        ids = sorted(
            p.stem for p in self.recipes.glob("*.yaml") if p.name != "index.yaml"
        )
        return ids
