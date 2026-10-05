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
_USAGE_WITH_MONTH = (
    "usage: python -m factory_target_py.expenses <csv-file> "
    "[--month YYYY-MM] [--budgets <budgets-csv>] [--top N]"
)


def _is_valid_month(month: str) -> bool:
    if len(month) != 7 or not _MONTH_PATTERN.match(month):
        return False
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        return False
    return True


def _parse_cli(argv: list[str]) -> tuple[Path, str | None, Path | None, int | None]:
    usage = _USAGE_LEGACY if "--month" not in argv and "--top" not in argv else _USAGE_WITH_MONTH

    def fail() -> None:
        print(usage, file=sys.stderr)
        raise SystemExit(1)

    if not argv:
        fail()

    expense_path = Path(argv[0])
    rest = argv[1:]
    month_filter: str | None = None
    budgets_path: Path | None = None
    top_count: int | None = None
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
        if token == "--top":
            if top_count is not None or index + 1 >= len(rest):
                fail()
            value = rest[index + 1]
            if value.startswith("--"):
                fail()
            if not value or any(character not in "0123456789" for character in value):
                print("--top requires a positive integer", file=sys.stderr)
                raise SystemExit(1)
            try:
                top_count = int(value)
            except ValueError:
                top_count = sys.maxsize
            if top_count <= 0:
                print("--top requires a positive integer", file=sys.stderr)
                raise SystemExit(1)
            index += 2
            continue
        fail()

    if month_filter is not None and not _is_valid_month(month_filter):
        fail()

    return expense_path, month_filter, budgets_path, top_count


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


def _top_categories_to_json(category_totals: dict[str, Decimal], count: int) -> list[dict]:
    ranked = sorted(category_totals.items(), key=lambda item: (-item[1], item[0]))
    return [
        {"category": category, "total": money_to_json_string(total)}
        for category, total in ranked[:count]
    ]


def main() -> None:
    expense_path, month_filter, budgets_path, top_count = _parse_cli(sys.argv[1:])

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

    payload: dict = {
        "category_totals": _decimal_map_to_json(category_totals),
        "month_totals": _decimal_map_to_json(month_totals),
        "errors": errors,
    }

    if month_filter is not None:
        payload["month"] = month_filter
    if top_count is not None:
        payload["top_categories"] = _top_categories_to_json(category_totals, top_count)

    if budgets_path is not None:
        try:
            budgets_text = budgets_path.read_text(encoding="utf-8")
        except OSError:
            print(str(budgets_path), file=sys.stderr)
            raise SystemExit(1) from None
        try:
            budgets = parse_budgets_csv(budgets_text)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        payload["budget_alerts"] = _alerts_to_json(
            compute_budget_alerts(month_category_totals, budgets)
        )

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
