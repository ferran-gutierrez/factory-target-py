"""CLI entry point for python -m factory_target_py.expenses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from factory_target_py.expenses import import_expenses


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "usage: python -m factory_target_py.expenses <csv-file>",
            file=sys.stderr,
        )
        raise SystemExit(1)

    csv_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    category_totals, month_totals, errors = import_expenses(csv_text)
    payload = {
        "category_totals": category_totals,
        "month_totals": month_totals,
        "errors": errors,
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
