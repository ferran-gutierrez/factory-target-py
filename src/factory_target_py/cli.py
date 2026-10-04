"""Console entry point for import-expenses."""

from __future__ import annotations

import sys
from pathlib import Path

from factory_target_py.expense_importer import parse_expense_csv


def main() -> None:
    if len(sys.argv) > 1:
        csv_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        csv_text = sys.stdin.read()

    result = parse_expense_csv(csv_text)

    print("Category totals:")
    for category in sorted(result.totals_by_category):
        print(f"  {category}: {result.totals_by_category[category]}")

    print("Month totals:")
    for month in sorted(result.totals_by_month):
        print(f"  {month}: {result.totals_by_month[month]}")

    if result.errors:
        print("Errors:")
        for err in result.errors:
            print(f"  Line {err.line}: {err.reason}")

    raise SystemExit(0)


if __name__ == "__main__":
    main()
