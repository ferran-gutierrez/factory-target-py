"""Mixed fixture import (REQ-12)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from factory_target_py.expenses import import_expenses

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "expenses_mixed.csv"


def test_mixed_fixture_totals_and_errors():
    csv_text = FIXTURE_PATH.read_text(encoding="utf-8")
    category_totals, month_totals, _, errors = import_expenses(csv_text)

    assert category_totals == {"Food": Decimal("20.00"), "Travel": Decimal("100.00")}
    assert month_totals == {
        "2024-01": Decimal("12.50"),
        "2024-02": Decimal("100.00"),
        "2024-03": Decimal("7.50"),
    }
    for value in category_totals.values():
        assert isinstance(value, Decimal)
    for value in month_totals.values():
        assert isinstance(value, Decimal)

    expected_errors = {
        (3, "wrong number of columns"),
        (5, "invalid date"),
        (6, "empty category"),
        (7, "empty description"),
        (8, "invalid amount"),
        (9, "invalid amount"),
    }
    actual_errors = {(entry["line"], entry["reason"]) for entry in errors}
    assert actual_errors == expected_errors
