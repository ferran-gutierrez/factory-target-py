"""Mixed fixture import (REQ-12)."""

from __future__ import annotations

from pathlib import Path

from factory_target_py.expenses import import_expenses

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "expenses_mixed.csv"


def test_mixed_fixture_totals_and_errors():
    csv_text = FIXTURE_PATH.read_text(encoding="utf-8")
    category_totals, month_totals, _, errors = import_expenses(csv_text)

    assert category_totals == {"Food": 20.0, "Travel": 100.0}
    assert month_totals == {"2024-01": 12.5, "2024-02": 100.0, "2024-03": 7.5}

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
