#!/usr/bin/env python3
"""Rename recipe originals to {recipe-slug}-{YYYYMMDD}.{ext} and update YAML references.

Only renames PDF and JPG sources linked from non-reference recipe YAML files
(those without X-flags: [index-page-not-a-recipe]). Reference/binder index files
are skipped.

Run from repo root or anywhere inside reciperepo. Use --apply to perform renames;
default is dry-run.

Maintains originals/original_rename_map.csv mapping original filenames to new ones
(planned on dry-run, applied after --apply) for later correction or reversal.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from recipe_tool.paths import RepoPaths

RECIPE_EXTENSIONS = {".pdf", ".jpg", ".jpeg"}
TARGET_NAME_RE = re.compile(r"^[a-z0-9-]+-\d{8}\.(pdf|jpg)$")
DEFAULT_MAPPING_FILE = "original_rename_map.csv"
MAPPING_FIELDS = ("original_filename", "new_filename", "recipe_id", "status", "timestamp")


@dataclass
class RenamePlan:
    recipe_id: str
    yaml_path: Path
    source_path: Path
    target_path: Path
    old_ref: str
    new_ref: str


def recipe_slug(recipe_id: str) -> str:
    if "." in recipe_id:
        return recipe_id.split(".", 1)[1]
    return recipe_id


def is_reference_entry(data: dict) -> bool:
    flags = data.get("X-flags") or []
    if isinstance(flags, str):
        flags = [flags]
    return "index-page-not-a-recipe" in flags


def source_file_date(path: Path) -> datetime:
    st = path.stat()
    ts = getattr(st, "st_birthtime", None)
    if ts is None or ts <= 0:
        ts = st.st_mtime
    return datetime.fromtimestamp(ts)


def target_extension(path: Path) -> str:
    suffix = path.suffix.lower()
    return ".jpg" if suffix in {".jpg", ".jpeg"} else suffix


def build_target_name(recipe_id: str, source_path: Path) -> str:
    slug = recipe_slug(recipe_id)
    date_stamp = source_file_date(source_path).strftime("%Y%m%d")
    ext = target_extension(source_path)
    return f"{slug}-{date_stamp}{ext}"


def already_renamed(recipe_id: str, filename: str) -> bool:
    if not TARGET_NAME_RE.match(filename):
        return False
    slug = recipe_slug(recipe_id)
    return filename.startswith(f"{slug}-")


def resolve_original(paths: RepoPaths, rel: str) -> Path | None:
    if not rel.startswith("../originals/"):
        return None
    name = Path(rel).name
    path = paths.originals / name
    return path if path.exists() else None


def update_yaml_reference(yaml_path: Path, old_ref: str, new_ref: str) -> None:
    text = yaml_path.read_text(encoding="utf-8")
    old_line = f"X-original-source: {old_ref}"
    new_line = f"X-original-source: {new_ref}"
    if old_line not in text:
        raise ValueError(f"{yaml_path}: expected line not found: {old_line}")
    yaml_path.write_text(text.replace(old_line, new_line, 1), encoding="utf-8")


def collect_rename_plans(paths: RepoPaths) -> tuple[list[RenamePlan], list[str]]:
    plans: list[RenamePlan] = []
    warnings: list[str] = []

    for yaml_path in sorted(paths.recipes.glob("*.yaml")):
        if yaml_path.name == "index.yaml":
            continue

        recipe_id = yaml_path.stem
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        if is_reference_entry(data):
            continue

        rel = data.get("X-original-source")
        if not rel:
            continue

        source_path = resolve_original(paths, rel)
        if source_path is None:
            abs_candidate = (yaml_path.parent / rel).resolve()
            if abs_candidate.exists():
                source_path = abs_candidate
            else:
                warnings.append(f"{recipe_id}: source not found: {rel}")
                continue

        if source_path.suffix.lower() not in RECIPE_EXTENSIONS:
            continue

        if already_renamed(recipe_id, source_path.name):
            continue

        target_name = build_target_name(recipe_id, source_path)
        target_path = paths.originals / target_name
        new_ref = f"../originals/{target_name}"

        if target_path.exists() and target_path.resolve() != source_path.resolve():
            warnings.append(
                f"{recipe_id}: target already exists: {target_name} "
                f"(from {source_path.name})"
            )
            continue

        plans.append(
            RenamePlan(
                recipe_id=recipe_id,
                yaml_path=yaml_path,
                source_path=source_path,
                target_path=target_path,
                old_ref=rel,
                new_ref=new_ref,
            )
        )

    return plans, warnings


def default_mapping_path(paths: RepoPaths) -> Path:
    return paths.originals / DEFAULT_MAPPING_FILE


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    mapping: dict[str, dict[str, str]] = {}
    for row in rows:
        original = row.get("original_filename", "").strip()
        if original:
            mapping[original] = {field: row.get(field, "") for field in MAPPING_FIELDS}
    return mapping


def write_mapping(
    path: Path,
    plans: list[RenamePlan],
    *,
    status: str,
    timestamp: str,
) -> None:
    existing = load_mapping(path)
    for plan in plans:
        existing[plan.source_path.name] = {
            "original_filename": plan.source_path.name,
            "new_filename": plan.target_path.name,
            "recipe_id": plan.recipe_id,
            "status": status,
            "timestamp": timestamp,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MAPPING_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for original in sorted(existing):
            writer.writerow(existing[original])


def apply_plans(
    plans: list[RenamePlan],
    *,
    dry_run: bool,
    mapping_path: Path,
) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = "planned" if dry_run else "applied"

    for plan in plans:
        print(f"{plan.recipe_id}:")
        print(f"  file: {plan.source_path.name} -> {plan.target_path.name}")
        print(f"  yaml: {plan.old_ref} -> {plan.new_ref}")
        if dry_run:
            continue
        if plan.source_path.resolve() != plan.target_path.resolve():
            plan.source_path.rename(plan.target_path)
        update_yaml_reference(plan.yaml_path, plan.old_ref, plan.new_ref)

    write_mapping(mapping_path, plans, status=status, timestamp=timestamp)
    print(f"\nMapping {'preview ' if dry_run else ''}written to {mapping_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rename recipe originals to {slug}-{YYYYMMDD}.{ext} "
            "and update X-original-source in recipe YAML"
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform renames and YAML updates (default: dry-run only)",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=None,
        help=f"CSV mapping file (default: originals/{DEFAULT_MAPPING_FILE})",
    )
    args = parser.parse_args()

    paths = RepoPaths()
    mapping_path = args.mapping or default_mapping_path(paths)
    plans, warnings = collect_rename_plans(paths)

    if warnings:
        print("Warnings:", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print(file=sys.stderr)

    if not plans:
        print("No files to rename.")
        return 0

    mode = "DRY RUN" if not args.apply else "APPLY"
    print(f"{mode}: {len(plans)} rename(s)\n")
    apply_plans(plans, dry_run=not args.apply, mapping_path=mapping_path)

    if not args.apply:
        print("Re-run with --apply to perform these changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
