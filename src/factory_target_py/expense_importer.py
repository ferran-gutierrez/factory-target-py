from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation


def import_expenses(csv_text: str) -> dict:
    by_category: dict[str, Decimal] = {}
    by_month: dict[str, Decimal] = {}
    errors: list[dict[str, int | str]] = []

    header_seen = False
    for line_num, line in enumerate(csv_text.splitlines(), start=1):
        if not line.strip():
            continue

        if not header_seen:
            header_seen = True
            continue

        row = next(csv.reader([line]))
        if len(row) != 4:
            errors.append({"line": line_num, "reason": "wrong column count"})
            continue

        date_str, category, description, amount_str = (field.strip() for field in row)

        try:
            parsed_date = date.fromisoformat(date_str)
        except ValueError:
            errors.append({"line": line_num, "reason": "invalid date"})
            continue

        if not category:
            errors.append({"line": line_num, "reason": "empty category"})
            continue

        if not description:
            errors.append({"line": line_num, "reason": "empty description"})
            continue

        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            errors.append({"line": line_num, "reason": "invalid amount"})
            continue

        if amount <= 0:
            errors.append({"line": line_num, "reason": "invalid amount"})
            continue

        by_category[category] = by_category.get(category, Decimal(0)) + amount
        month_key = f"{parsed_date.year:04d}-{parsed_date.month:02d}"
        by_month[month_key] = by_month.get(month_key, Decimal(0)) + amount

    return {
        "by_category": by_category,
        "by_month": by_month,
        "errors": errors,
    }
