from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .paths import RepoPaths

# Homepage-only URLs (no recipe path)
BARE_URL_HOSTS = {
    "www.allrecipes.com",
    "allrecipes.com",
    "www.foodnetwork.com",
    "foodnetwork.com",
    "www.minimalistbaker.com",
    "minimalistbaker.com",
    "www.spendwithpennies.com",
    "spendwithpennies.com",
    "www.tasteofhome.com",
    "tasteofhome.com",
}


@dataclass
class AuditIssue:
    recipe_id: str
    code: str
    message: str


@dataclass
class AuditReport:
    issues: list[AuditIssue] = field(default_factory=list)

    def add(self, recipe_id: str, code: str, message: str) -> None:
        self.issues.append(AuditIssue(recipe_id, code, message))

    def by_code(self) -> dict[str, list[AuditIssue]]:
        grouped: dict[str, list[AuditIssue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.code, []).append(issue)
        return grouped


def _is_bare_source_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return False
    path = (parsed.path or "").strip("/")
    if not path:
        return True
    host = parsed.netloc.lower()
    if host not in BARE_URL_HOSTS and host.removeprefix("www.") not in {
        h.removeprefix("www.") for h in BARE_URL_HOSTS
    }:
        return False
    # Known sites: flag if URL has no /recipe/ or similar deep path
    segments = path.split("/")
    if len(segments) <= 1:
        return True
    if host.endswith("allrecipes.com") and "recipe" not in path.lower():
        return True
    if host.endswith("foodnetwork.com") and len(segments) < 2:
        return True
    return False


def _category_is_list(data: dict) -> bool:
    cat = data.get("X-category")
    if cat is None:
        return False
    return isinstance(cat, list)


def audit_recipe(recipe_id: str, data: dict) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    flags = data.get("X-flags") or []
    if isinstance(flags, str):
        flags = [flags]
    is_reference = "index-page-not-a-recipe" in flags

    if is_reference:
        if not _category_is_list(data) and data.get("X-category") != "reference":
            issues.append(
                AuditIssue(
                    recipe_id,
                    "reference-category",
                    "index/reference entry should have X-category: [reference]",
                )
            )
        return issues

    if not data.get("recipe_name"):
        issues.append(AuditIssue(recipe_id, "missing-name", "missing recipe_name"))

    if data.get("author") and not data.get("source_authors"):
        issues.append(
            AuditIssue(
                recipe_id,
                "legacy-author",
                "uses 'author:' — prefer source_authors: list",
            )
        )

    if not _category_is_list(data):
        if data.get("X-category") is None:
            issues.append(AuditIssue(recipe_id, "missing-category", "missing X-category"))
        else:
            issues.append(
                AuditIssue(
                    recipe_id,
                    "category-format",
                    "X-category should be a list (e.g. [dinner])",
                )
            )

    tags = data.get("X-tags")
    if not tags:
        issues.append(AuditIssue(recipe_id, "missing-tags", "missing X-tags"))

    ver = data.get("X-source-verification")
    if not ver:
        if data.get("X-flags") == [] or flags == []:
            issues.append(
                AuditIssue(
                    recipe_id,
                    "empty-flags-only",
                    "X-flags: [] but no X-source-verification block",
                )
            )
        else:
            issues.append(
                AuditIssue(
                    recipe_id,
                    "missing-verification",
                    "missing X-source-verification",
                )
            )
    elif isinstance(ver, dict):
        status = ver.get("status")
        if not status:
            issues.append(
                AuditIssue(recipe_id, "verification-status", "verification missing status")
            )
        elif status not in ("verified", "needs-review", "needs-manual-review"):
            issues.append(
                AuditIssue(
                    recipe_id,
                    "verification-status",
                    f"unknown verification status: {status!r}",
                )
            )

    source_url = data.get("source_url")
    if source_url and _is_bare_source_url(str(source_url)):
        issues.append(
            AuditIssue(
                recipe_id,
                "bare-source-url",
                f"source_url is site homepage only: {source_url}",
            )
        )

    if not source_url and not data.get("X-original-source") and not is_reference:
        issues.append(
            AuditIssue(
                recipe_id,
                "missing-provenance",
                "no source_url and no X-original-source",
            )
        )

    if source_url and not data.get("X-original-source"):
        pass  # OK for web-only sources
    if not source_url and data.get("X-original-source"):
        pass  # OK for custom cards

    return issues


def audit_all(paths: RepoPaths | None = None) -> AuditReport:
    paths = paths or RepoPaths()
    report = AuditReport()

    for recipe_id in paths.list_recipe_ids():
        yaml_path = paths.recipe_yaml(recipe_id)
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception as exc:
            report.add(recipe_id, "parse-error", str(exc))
            continue
        if not isinstance(data, dict):
            report.add(recipe_id, "parse-error", "YAML root is not a mapping")
            continue
        for issue in audit_recipe(recipe_id, data):
            report.issues.append(issue)

    return report


def format_report(report: AuditReport, *, verbose: bool = False) -> str:
    if not report.issues:
        return "No metadata issues found.\n"

    grouped = report.by_code()
    lines = [f"Metadata audit: {len(report.issues)} issue(s) across recipes\n"]

    for code in _CODE_ORDER:
        items = grouped.get(code, [])
        if not items:
            continue
        lines.append(f"\n{code} ({len(items)})")
        for issue in sorted(items, key=lambda i: i.recipe_id):
            lines.append(f"  {issue.recipe_id}: {issue.message}")

    if verbose:
        other = set(grouped) - set(_CODE_ORDER)
        for code in sorted(other):
            lines.append(f"\n{code} ({len(grouped[code])})")
            for issue in grouped[code]:
                lines.append(f"  {issue.recipe_id}: {issue.message}")

    recipe_ids = {i.recipe_id for i in report.issues}
    lines.append(f"\nRecipes with issues: {len(recipe_ids)}")
    return "\n".join(lines) + "\n"


AUDIT_SCRIPT_NAME = "audit_metadata"

_CODE_ORDER = [
    "parse-error",
    "reference-category",
    "missing-name",
    "legacy-author",
    "missing-category",
    "category-format",
    "missing-tags",
    "missing-verification",
    "empty-flags-only",
    "verification-status",
    "bare-source-url",
    "missing-provenance",
]


def audit_log_path(
    script_dir: Path | None = None,
    *,
    on_date: date | None = None,
    paths: RepoPaths | None = None,
) -> Path:
    """Return `{script_dir}/{AUDIT_SCRIPT_NAME}-YYYYMMDD.md`."""
    directory = script_dir or (paths or RepoPaths()).root / "scripts"
    stamp = on_date or date.today()
    return directory / f"{AUDIT_SCRIPT_NAME}-{stamp:%Y%m%d}.md"


def format_report_md(report: AuditReport, *, verbose: bool = False) -> str:
    stamp = date.today()
    if not report.issues:
        return (
            f"# Recipe metadata audit\n\n"
            f"**Date:** {stamp:%Y-%m-%d}\n\n"
            f"No metadata issues found.\n"
        )

    grouped = report.by_code()
    recipe_ids = {i.recipe_id for i in report.issues}
    lines = [
        "# Recipe metadata audit",
        "",
        f"**Date:** {stamp:%Y-%m-%d}",
        f"**Issues:** {len(report.issues)} across {len(recipe_ids)} recipe(s)",
        "",
    ]

    for code in _CODE_ORDER:
        items = grouped.get(code, [])
        if not items:
            continue
        lines.append(f"## {code} ({len(items)})")
        lines.append("")
        for issue in sorted(items, key=lambda i: i.recipe_id):
            lines.append(f"- `{issue.recipe_id}` — {issue.message}")
        lines.append("")

    if verbose:
        other = set(grouped) - set(_CODE_ORDER)
        for code in sorted(other):
            lines.append(f"## {code} ({len(grouped[code])})")
            lines.append("")
            for issue in grouped[code]:
                lines.append(f"- `{issue.recipe_id}` — {issue.message}")
            lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Recipes with issues: {len(recipe_ids)}")
    lines.append(f"- Total issues: {len(report.issues)}")
    lines.append("")
    return "\n".join(lines)


def write_audit_log(
    report: AuditReport,
    *,
    verbose: bool = False,
    script_dir: Path | None = None,
    paths: RepoPaths | None = None,
) -> Path:
    log_path = audit_log_path(script_dir, paths=paths)
    log_path.write_text(format_report_md(report, verbose=verbose), encoding="utf-8")
    return log_path
