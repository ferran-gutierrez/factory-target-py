"""CLI entry point for python -m factory_target_py.expenses."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from factory_target_py.expenses import (
    compute_budget_alerts,
    import_expenses,
    money_to_json_string,
    parse_budgets_csv,
)

_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def _is_valid_month(month: str) -> bool:
    if len(month) != 7 or not _MONTH_PATTERN.match(month):
        return False
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        return False
    return True


def _build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="python -m factory_target_py.expenses",
        usage=(
            "usage: python -m factory_target_py.expenses <csv-file> "
            "[--month YYYY-MM] [--budgets <budgets-csv>]"
        ),
    )


def _parse_cli(argv: list[str]) -> tuple[Path, str | None, Path | None]:
    parser = _build_parser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--month", dest="month")
    parser.add_argument("--budgets", dest="budgets", metavar="budgets-csv")

    args = parser.parse_args(argv)

    if args.month is not None and not _is_valid_month(args.month):
        parser.print_usage(file=sys.stderr)
        raise SystemExit(1)

    budgets_path = Path(args.budgets) if args.budgets is not None else None
    return args.csv_file, args.month, budgets_path


def _decimal_map_to_json(d: dict[str, Decimal]) -> dict[str, str]:
    return {key: money_to_json_string(value) for key, value in d.items()}


def _alerts_to_json(alerts: list[dict]) -> list[dict]:
    result: list[dict] = []
    for alert in alerts:
        result.append(
            {
                "month": alert["month"],
                "category": alert["category"],
                "total": money_to_json_string(alert["total"]),
                "limit": money_to_json_string(alert["limit"]),
                "amount_over": money_to_json_string(alert["amount_over"]),
            }
        )
    return result


def main() -> None:
    expense_path, month_filter, budgets_path = _parse_cli(sys.argv[1:])

    csv_text = expense_path.read_text(encoding="utf-8")
    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)

    if month_filter is not None:
        category_totals = dict(month_category_totals.get(month_filter, {}))
        month_totals = (
            {month_filter: month_totals[month_filter]} if month_filter in month_totals else {}
        )
        month_category_totals = {month_filter: dict(category_totals)}

    payload: dict = {
        "category_totals": _decimal_map_to_json(category_totals),
        "month_totals": _decimal_map_to_json(month_totals),
        "errors": errors,
    }

    if month_filter is not None:
        payload["month"] = month_filter

    if budgets_path is not None:
        try:
            budgets_text = budgets_path.read_text(encoding="utf-8")
            budgets = parse_budgets_csv(budgets_text)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        payload["budget_alerts"] = _alerts_to_json(
            compute_budget_alerts(month_category_totals, budgets)
        )

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
