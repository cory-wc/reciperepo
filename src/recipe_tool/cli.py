from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .extract.runner import run_extract, run_extract_pending
from .index import generate_index
from .load import dump_recipe
from .paths import RepoPaths
from .pdf import generate_all_pdfs, generate_index_pdf, generate_recipe_pdf
from .render import render_all_recipes, render_recipe_html
from .shop import format_shopping_list
from .metadata_audit import audit_all, format_report
from .status import full_status, pending_extractions
from .validate import validate_all, validate_recipe_id


def _resolve_targets(args: argparse.Namespace, paths: RepoPaths) -> list[str]:
    if getattr(args, "all", False):
        return paths.list_recipe_ids()
    if args.recipe_id == "index":
        return []
    if args.recipe_id:
        return [args.recipe_id]
    raise SystemExit("Provide a recipe id or --all")


def cmd_validate(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    if args.all:
        errors = validate_all(paths)
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            return 1
        print(f"All {len(paths.list_recipe_ids())} recipes valid.")
        return 0
    validate_recipe_id(args.recipe_id, paths)
    print(f"OK: {args.recipe_id}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    targets = _resolve_targets(args, paths)
    for rid in targets:
        out = render_recipe_html(rid, paths, mode="screen")
        print(f"Wrote {paths.recipe_html(rid)}")
    if args.all or len(targets) > 1:
        from .index import render_index_html

        render_index_html(paths, allow_missing=args.allow_missing)
        print(f"Wrote {paths.index_html()}")
    return 0


def cmd_pdf(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    if args.recipe_id == "index":
        out = generate_index_pdf(paths)
        print(f"Wrote {out}")
        return 0
    if args.all:
        for p in generate_all_pdfs(paths):
            print(f"Wrote {p}")
        return 0
    generate_recipe_pdf(args.recipe_id, paths)
    print(f"Wrote {paths.recipe_pdf(args.recipe_id)}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    generate_index(paths, by=args.by, allow_missing=args.allow_missing, include_pdf=True)
    print(f"Wrote {paths.index_yaml()}, {paths.index_html()}, {paths.index_pdf()}")
    return 0


def cmd_shop(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    text = format_shopping_list(args.recipe_ids, paths)
    if args.output:
        out = paths.lists / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(text, end="")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    for line in full_status(paths):
        print(f"[{line.kind:7}] {line.recipe_id}: {line.message}")
    pending = pending_extractions(paths)
    if pending:
        print(f"\nUnreferenced originals ({len(pending)} files) — candidates for extract --pending")
    return 0


def cmd_audit_metadata(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    report = audit_all(paths)
    print(format_report(report, verbose=args.verbose), end="")
    return 1 if args.fail and report.issues else 0


def cmd_new(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    out = paths.recipe_yaml(args.recipe_id)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} already exists")
    stub = {
        "recipe_uuid": args.recipe_id,
        "recipe_name": args.recipe_id.split(".")[-1].replace("-", " ").title(),
        "yields": [{"amount": 4, "unit": "servings"}],
        "ingredients": [{"example ingredient": {"amounts": [{"amount": 1, "unit": "cup"}]}}],
        "steps": [{"step": "Describe the first step."}],
        "X-source-verification": {"status": "needs-review", "notes": []},
    }
    dump_recipe(stub, out)
    print(f"Wrote {out}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    paths = RepoPaths()
    if args.pending:
        ids = run_extract_pending(paths, dry_run=args.dry_run)
        print(f"Processed {len(ids)} recipes")
        return 0
    source = Path(args.source) if args.source else None
    out = run_extract(
        args.recipe_id,
        args.url,
        source,
        paths,
        dry_run=args.dry_run,
        force=args.force,
    )
    if out:
        print(f"Wrote {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="recipe", description="ORF recipe collection tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="Validate ORF YAML")
    p.add_argument("recipe_id", nargs="?", help="Recipe id (namespace.slug)")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("render", help="Render screen HTML to site/")
    p.add_argument("recipe_id", nargs="?", help="Recipe id or omit with --all")
    p.add_argument("--all", action="store_true")
    p.add_argument("--allow-missing", action="store_true")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("pdf", help="Generate PDF in pdfs/")
    p.add_argument("recipe_id", nargs="?", help="Recipe id, 'index', or omit with --all")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_pdf)

    p = sub.add_parser("index", help="Regenerate index.yaml, site/index.html, pdfs/index.pdf")
    p.add_argument("--by", choices=["name", "tag", "category"], default="name")
    p.add_argument("--allow-missing", action="store_true")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("shop", help="Merged shopping list")
    p.add_argument("recipe_ids", nargs="+", help="One or more recipe ids")
    p.add_argument("-o", "--output", help="Write to lists/FILE")
    p.set_defaults(func=cmd_shop)

    p = sub.add_parser("status", help="Migration and artifact status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser(
        "audit-metadata",
        help="Report metadata gaps (category, bare URL, verification, etc.)",
    )
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--fail", action="store_true", help="Exit 1 if issues found")
    p.set_defaults(func=cmd_audit_metadata)

    p = sub.add_parser("new", help="Scaffold a new recipe YAML")
    p.add_argument("recipe_id")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("extract", help="Extract ORF YAML from URL or file")
    p.add_argument("recipe_id", nargs="?", help="Target recipe id")
    p.add_argument("--url", help="Recipe page URL")
    p.add_argument("--source", help="Path under originals/ or absolute")
    p.add_argument("--pending", action="store_true", help="Bulk extract unreferenced originals")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_extract)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
