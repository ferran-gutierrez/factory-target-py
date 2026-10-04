"""CLI entry point for python -m factory_target_py.expenses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from factory_target_py.expenses import (
    compute_budget_alerts,
    import_expenses,
    parse_budgets_csv,
)

_USAGE = "usage: python -m factory_target_py.expenses <csv-file> [--budgets <budgets-csv>]"


def main() -> None:
    argc = len(sys.argv)
    if argc not in (2, 4):
        print(_USAGE, file=sys.stderr)
        raise SystemExit(1)

    expense_path = Path(sys.argv[1])
    budgets_path: Path | None = None
    if argc == 4:
        if sys.argv[2] != "--budgets":
            print(_USAGE, file=sys.stderr)
            raise SystemExit(1)
        budgets_path = Path(sys.argv[3])

    csv_text = expense_path.read_text(encoding="utf-8")
    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)
    payload: dict = {
        "category_totals": category_totals,
        "month_totals": month_totals,
        "errors": errors,
    }

    if budgets_path is not None:
        try:
            budgets_text = budgets_path.read_text(encoding="utf-8")
            budgets = parse_budgets_csv(budgets_text)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        payload["budget_alerts"] = compute_budget_alerts(month_category_totals, budgets)

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
