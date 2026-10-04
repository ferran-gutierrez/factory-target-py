"""CSV expense import and aggregation."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def import_expenses(csv_text: str) -> tuple[dict[str, float], dict[str, float], list[dict]]:
    category_totals: dict[str, float] = {}
    month_totals: dict[str, float] = {}
    errors: list[dict] = []

    lines = csv_text.splitlines()
    if not lines:
        return category_totals, month_totals, errors

    for line_num, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue

        row = next(csv.reader([line]))
        if len(row) != 4:
            errors.append({"line": line_num, "reason": "wrong number of columns"})
            continue

        date_s, category, description, amount_s = (field.strip() for field in row)
        if not date_s and not category and not description and not amount_s:
            continue

        if not _is_valid_date(date_s):
            errors.append({"line": line_num, "reason": "invalid date"})
            continue
        if not category:
            errors.append({"line": line_num, "reason": "empty category"})
            continue
        if not description:
            errors.append({"line": line_num, "reason": "empty description"})
            continue

        amount = _parse_positive_amount(amount_s)
        if amount is None:
            errors.append({"line": line_num, "reason": "invalid amount"})
            continue

        category_totals[category] = category_totals.get(category, 0.0) + amount
        month_key = date_s[:7]
        month_totals[month_key] = month_totals.get(month_key, 0.0) + amount

    return category_totals, month_totals, errors


def _is_valid_date(date_s: str) -> bool:
    if not _DATE_PATTERN.match(date_s):
        return False
    try:
        datetime.strptime(date_s, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _parse_positive_amount(amount_s: str) -> float | None:
    try:
        value = Decimal(amount_s)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return float(value)
