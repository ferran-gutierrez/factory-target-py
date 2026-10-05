"""CLI entry point for python -m factory_target_py.expenses."""

from __future__ import annotations

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
_USAGE_LEGACY = "usage: python -m factory_target_py.expenses <csv-file> [--budgets <budgets-csv>]"
_USAGE_WITH_OPTS = (
    "usage: python -m factory_target_py.expenses <csv-file> "
    "[--format json|csv] [--month YYYY-MM] [--budgets <budgets-csv>]"
)
_VALID_FORMATS = frozenset({"json", "csv"})


def _is_valid_month(month: str) -> bool:
    if len(month) != 7 or not _MONTH_PATTERN.match(month):
        return False
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        return False
    return True


def _cli_usage(argv: list[str]) -> str:
    if any(token in argv for token in ("--month", "--format", "--budgets")):
        return _USAGE_WITH_OPTS
    return _USAGE_LEGACY


def _parse_cli(argv: list[str]) -> tuple[Path, str | None, Path | None, str]:
    usage = _cli_usage(argv)

    def fail() -> None:
        print(usage, file=sys.stderr)
        raise SystemExit(1)

    if not argv:
        fail()

    expense_path = Path(argv[0])
    rest = argv[1:]
    month_filter: str | None = None
    budgets_path: Path | None = None
    output_format = "json"
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "--month":
            if month_filter is not None:
                fail()
            if index + 1 >= len(rest):
                fail()
            month_filter = rest[index + 1]
            index += 2
            continue
        if token == "--budgets":
            if budgets_path is not None:
                fail()
            if index + 1 >= len(rest):
                fail()
            budgets_path = Path(rest[index + 1])
            index += 2
            continue
        if token == "--format":
            if index + 1 >= len(rest):
                fail()
            fmt = rest[index + 1]
            if fmt not in _VALID_FORMATS:
                fail()
            output_format = fmt
            index += 2
            continue
        fail()

    if month_filter is not None and not _is_valid_month(month_filter):
        fail()

    return expense_path, month_filter, budgets_path, output_format


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


def _print_csv_category_totals(category_totals_json: dict[str, str]) -> None:
    lines = ["category,total"]
    for key in sorted(category_totals_json.keys()):
        lines.append(f"{key},{category_totals_json[key]}")
    sys.stdout.write("\n".join(lines) + "\n")


def _load_budgets(budgets_path: Path) -> dict:
    try:
        budgets_text = budgets_path.read_text(encoding="utf-8")
    except OSError:
        print(str(budgets_path), file=sys.stderr)
        raise SystemExit(1) from None
    try:
        return parse_budgets_csv(budgets_text)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    expense_path, month_filter, budgets_path, output_format = _parse_cli(sys.argv[1:])

    try:
        csv_text = expense_path.read_text(encoding="utf-8")
    except OSError:
        print(str(expense_path), file=sys.stderr)
        raise SystemExit(1) from None

    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)

    if month_filter is not None:
        category_totals = dict(month_category_totals.get(month_filter, {}))
        month_totals = (
            {month_filter: month_totals[month_filter]} if month_filter in month_totals else {}
        )
        month_category_totals = {month_filter: dict(category_totals)}

    category_totals_json = _decimal_map_to_json(category_totals)

    budget_alerts_json: list[dict] | None = None
    if budgets_path is not None:
        budgets = _load_budgets(budgets_path)
        if output_format == "json":
            budget_alerts_json = _alerts_to_json(
                compute_budget_alerts(month_category_totals, budgets)
            )

    if output_format == "csv":
        for err in errors:
            print(f"line {err['line']}: {err['reason']}", file=sys.stderr)
        _print_csv_category_totals(category_totals_json)
        return

    payload: dict = {
        "category_totals": category_totals_json,
        "month_totals": _decimal_map_to_json(month_totals),
        "errors": errors,
    }

    if month_filter is not None:
        payload["month"] = month_filter

    if budget_alerts_json is not None:
        payload["budget_alerts"] = budget_alerts_json

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
