"""Parse and validate expense CSV text."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

_REQUIRED_COLUMNS = ("date", "category", "description", "amount")


@dataclass
class ExpenseLineError:
    line: int
    reason: str


@dataclass
class ExpenseParseResult:
    totals_by_category: dict[str, Decimal] = field(default_factory=dict)
    totals_by_month: dict[str, Decimal] = field(default_factory=dict)
    errors: list[ExpenseLineError] = field(default_factory=list)


def _parse_row(line: str) -> list[str]:
    reader = csv.reader([line])
    return next(reader)


def _header_indices(header_fields: list[str]) -> dict[str, int] | None:
    lowered = [name.strip().lower() for name in header_fields]
    indices: dict[str, int] = {}
    for col in _REQUIRED_COLUMNS:
        try:
            indices[col] = lowered.index(col)
        except ValueError:
            return None
    return indices


def _validate_date(raw: str, line: int) -> tuple[date | None, ExpenseLineError | None]:
    if not raw:
        return None, ExpenseLineError(line, "Invalid date: value is missing or blank")
    if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
        return None, ExpenseLineError(line, "Invalid date: must be YYYY-MM-DD")
    try:
        year = int(raw[0:4])
        month = int(raw[5:7])
        day = int(raw[8:10])
        parsed = date(year, month, day)
    except ValueError:
        return None, ExpenseLineError(line, "Invalid date: not a valid calendar date")
    iso = parsed.isoformat()
    if iso != raw:
        return None, ExpenseLineError(line, "Invalid date: not a valid calendar date")
    return parsed, None


def _validate_amount(raw: str, line: int) -> tuple[Decimal | None, ExpenseLineError | None]:
    if not raw:
        return None, ExpenseLineError(line, "Invalid amount: value is missing or blank")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None, ExpenseLineError(line, "Invalid amount: not a decimal number")
    if value <= 0:
        return None, ExpenseLineError(line, "Invalid amount: must be greater than zero")
    return value, None


def parse_expense_csv(csv_text: str) -> ExpenseParseResult:
    result = ExpenseParseResult()
    if not csv_text:
        return result

    lines = csv_text.splitlines()
    if not lines:
        return result

    header_fields = _parse_row(lines[0])
    indices = _header_indices(header_fields)
    if indices is None:
        return result

    date_idx = indices["date"]
    category_idx = indices["category"]
    description_idx = indices["description"]
    amount_idx = indices["amount"]
    max_idx = max(date_idx, category_idx, description_idx, amount_idx)

    for line_num, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue

        fields = _parse_row(line)
        if len(fields) <= max_idx:
            result.errors.append(
                ExpenseLineError(
                    line_num,
                    "Missing or invalid columns in row",
                )
            )
            continue

        date_raw = fields[date_idx].strip()
        category_raw = fields[category_idx].strip()
        description_raw = fields[description_idx].strip()
        amount_raw = fields[amount_idx].strip()

        parsed_date, date_err = _validate_date(date_raw, line_num)
        if date_err is not None:
            result.errors.append(date_err)
            continue

        if not category_raw:
            result.errors.append(ExpenseLineError(line_num, "Empty category field"))
            continue

        if not description_raw:
            result.errors.append(ExpenseLineError(line_num, "Empty description field"))
            continue

        parsed_amount, amount_err = _validate_amount(amount_raw, line_num)
        if amount_err is not None:
            result.errors.append(amount_err)
            continue

        month_key = parsed_date.isoformat()[:7]
        result.totals_by_category[category_raw] = (
            result.totals_by_category.get(category_raw, Decimal("0")) + parsed_amount
        )
        result.totals_by_month[month_key] = (
            result.totals_by_month.get(month_key, Decimal("0")) + parsed_amount
        )

    return result
