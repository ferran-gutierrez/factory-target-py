"""CSV expense import and aggregation."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TWO_PLACES = Decimal("0.01")
_ZERO = Decimal("0")


def _resolve_category_key(categories: dict[str, object], category: str) -> str:
    folded = category.casefold()
    for key in categories:
        if key.casefold() == folded:
            return key
    return category


def money_to_json_string(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))


def import_expenses(
    csv_text: str,
) -> tuple[
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, dict[str, Decimal]],
    list[dict],
]:
    category_totals: dict[str, Decimal] = {}
    month_totals: dict[str, Decimal] = {}
    month_category_totals: dict[str, dict[str, Decimal]] = {}
    errors: list[dict] = []
    canonical_by_normalized: dict[str, str] = {}

    lines = csv_text.splitlines()
    if not lines:
        return category_totals, month_totals, month_category_totals, errors

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

        normalized = category.casefold()
        if normalized not in canonical_by_normalized:
            canonical_by_normalized[normalized] = category
        category_key = canonical_by_normalized[normalized]
        category_totals[category_key] = category_totals.get(category_key, _ZERO) + amount
        month_key = date_s[:7]
        month_totals[month_key] = month_totals.get(month_key, _ZERO) + amount
        month_cats = month_category_totals.setdefault(month_key, {})
        month_cats[category_key] = month_cats.get(category_key, _ZERO) + amount

    return category_totals, month_totals, month_category_totals, errors


def compute_budget_alerts(
    month_category_totals: dict[str, dict[str, Decimal | float]],
    budgets: dict[str, Decimal | float],
) -> list[dict]:
    alerts: list[dict] = []
    for month in sorted(month_category_totals):
        cats = month_category_totals[month]
        month_alerts: list[dict] = []
        for budget_category in budgets:
            expense_category = _resolve_category_key(cats, budget_category)
            total = _coerce_decimal(cats.get(expense_category, _ZERO))
            limit = _coerce_decimal(budgets[budget_category])
            if total > limit:
                month_alerts.append(
                    {
                        "month": month,
                        "category": expense_category,
                        "total": total,
                        "limit": limit,
                        "amount_over": total - limit,
                    }
                )
        month_alerts.sort(key=lambda alert: alert["category"].casefold())
        alerts.extend(month_alerts)
    return alerts


def parse_budgets_csv(csv_text: str) -> dict[str, Decimal]:
    lines = csv_text.splitlines()
    if not lines:
        return {}

    header = next(csv.reader([lines[0]]))
    header_lower = {field.strip().lower() for field in header}
    if "category" not in header_lower or "limit" not in header_lower:
        msg = "missing required header columns"
        raise ValueError(msg)

    budgets: dict[str, Decimal] = {}
    seen_normalized: set[str] = set()
    for line in lines[1:]:
        if not line.strip():
            continue
        row = next(csv.reader([line]))
        if len(row) != 2:
            msg = "wrong number of columns"
            raise ValueError(msg)
        category, limit_s = (field.strip() for field in row)
        if not category and not limit_s:
            continue
        if not category:
            msg = "empty category"
            raise ValueError(msg)
        limit = _parse_positive_amount(limit_s)
        if limit is None:
            msg = "invalid limit"
            raise ValueError(msg)
        normalized = category.casefold()
        if normalized in seen_normalized:
            msg = "duplicate category"
            raise ValueError(msg)
        seen_normalized.add(normalized)
        budgets[category] = limit

    return budgets


def _coerce_decimal(value: Decimal | float | int) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _is_valid_date(date_s: str) -> bool:
    if not _DATE_PATTERN.match(date_s):
        return False
    try:
        datetime.strptime(date_s, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _parse_positive_amount(amount_s: str) -> Decimal | None:
    try:
        value = Decimal(amount_s)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value
