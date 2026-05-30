#!/usr/bin/env python3
"""Audit recipe YAML metadata. Run from repo root or anywhere inside reciperepo."""

from __future__ import annotations

import argparse
import sys

from recipe_tool.metadata_audit import audit_all, format_report
from recipe_tool.paths import RepoPaths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report metadata gaps in recipes/*.yaml (category, URLs, verification, etc.)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include unknown issue codes in output",
    )
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Exit 1 if any issues found (for CI)",
    )
    args = parser.parse_args()

    paths = RepoPaths()
    report = audit_all(paths)
    print(format_report(report, verbose=args.verbose), end="")

    if args.fail and report.issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
