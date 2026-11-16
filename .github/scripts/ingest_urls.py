"""Queue up to five recipe URLs from the Add a recipe workflow.

Reads URL_1..URL_5, RECIPE_ID, and USE_BROWSER from the environment so the
workflow script never interpolates the form values.
"""

from __future__ import annotations

import json
import os
import sys

import yaml

from recipe_tool.add import add_many
from recipe_tool.index import generate_index
from recipe_tool.paths import RepoPaths
from recipe_tool.pdf import generate_recipe_pdf
from recipe_tool.render import render_recipe_html
from recipe_tool.validate import validate_recipe_id


def yaml_recipe_name(path) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return str(data.get("recipe_name") or "")
    return ""


def main() -> int:
    urls = [os.environ.get(f"URL_{index}", "") for index in range(1, 6)]
    browser = os.environ.get("USE_BROWSER", "").lower() == "true"
    recipe_id = os.environ.get("RECIPE_ID", "").strip() or None
    paths = RepoPaths()
    try:
        successes, failures = add_many(urls, paths, recipe_id=recipe_id, browser=browser)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    report_dir = paths.root / "build"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {"successes": successes, "failures": failures}
    (report_dir / "ingest-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not successes:
        print("Every URL failed. No pull request will be opened.", file=sys.stderr)
        return 1

    for item in successes:
        recipe_id = item["recipe_id"]
        validate_recipe_id(recipe_id, paths)
        render_recipe_html(recipe_id, paths, mode="screen")
        generate_recipe_pdf(recipe_id, paths)
    generate_index(paths, allow_missing=True, include_pdf=True)

    lines = ["## Added recipes", ""]
    title = f"Add {len(successes)} recipes"
    if len(successes) == 1:
        recipe_id = successes[0]["recipe_id"]
        data = yaml_recipe_name(paths.recipe_yaml(recipe_id))
        title = f"Add {data or recipe_id}"
    for item in successes:
        lines.append(f"- `{item['recipe_id']}` from {item['url']}")
        yaml_path = paths.recipe_yaml(item["recipe_id"])
        notes = []
        if yaml_path.exists():
            text = yaml_path.read_text(encoding="utf-8")
            if "needs-review" in text:
                notes.append("status: needs-review")
        if notes:
            lines.append(f"  - {', '.join(notes)}")
    if failures:
        lines.extend(["", "## Failed", ""])
        for item in failures:
            lines.append(f"- {item['url']}: {item['error']}")
    lines.extend(
        [
            "",
            "Read the YAML and the generated HTML in this pull request. "
            "Amounts and tags are marked needs-review.",
        ]
    )
    (report_dir / "pr-body.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    first = successes[0]["recipe_id"]
    (report_dir / "ingest-branch.txt").write_text(f"ingest/{first}\n", encoding="utf-8")
    (report_dir / "ingest-title.txt").write_text(title + "\n", encoding="utf-8")
    print(first)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
