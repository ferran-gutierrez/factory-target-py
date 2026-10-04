"""Budget alerts, month_category_totals, and parse_budgets_csv (REQ-1 through REQ-10)."""

from __future__ import annotations

import pytest

from factory_target_py.expenses import (
    compute_budget_alerts,
    import_expenses,
    parse_budgets_csv,
)


def test_compute_budget_alerts_emits_alert_with_required_fields_when_over_budget():
    month_category_totals = {"2024-05": {"Food": 120.0}}
    budgets = {"Food": 100.0}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert len(alerts) == 1
    alert = alerts[0]
    assert set(alert.keys()) == {"month", "category", "total", "limit", "amount_over"}
    assert alert["month"] == "2024-05"
    assert alert["category"] == "Food"
    assert alert["total"] == 120.0
    assert alert["limit"] == 100.0
    assert alert["amount_over"] == 20.0


def test_compute_budget_alerts_ignores_categories_absent_from_budgets():
    month_category_totals = {
        "2024-01": {"Food": 500.0, "Travel": 800.0},
    }
    budgets = {"Food": 10.0}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert len(alerts) == 1
    assert alerts[0]["category"] == "Food"


def test_compute_budget_alerts_no_alert_when_total_at_or_under_limit():
    month_category_totals = {
        "2024-01": {"Food": 100.0},
        "2024-02": {"Food": 99.99},
    }
    budgets = {"Food": 100.0}

    assert compute_budget_alerts(month_category_totals, budgets) == []


def test_compute_budget_alerts_missing_inner_category_treated_as_zero_total():
    month_category_totals = {"2024-03": {"Travel": 50.0}}
    budgets = {"Food": 25.0}

    assert compute_budget_alerts(month_category_totals, budgets) == []


def test_compute_budget_alerts_ordered_by_month_then_category():
    month_category_totals = {
        "2024-02": {"Food": 50.0},
        "2024-01": {"Travel": 40.0, "Food": 30.0},
    }
    budgets = {"Food": 1.0, "Travel": 1.0}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert [(a["month"], a["category"]) for a in alerts] == [
        ("2024-01", "Food"),
        ("2024-01", "Travel"),
        ("2024-02", "Food"),
    ]


def test_import_expenses_returns_month_category_totals_consistent_with_other_totals():
    csv_text = (
        "date,category,description,amount\n"
        "2024-01-10,Food,Lunch,10.00\n"
        "2024-01-20,Food,Dinner,5.50\n"
        "2024-02-01,Travel,Flight,100.00\n"
        "2024-01-25,travel,Train,20.00\n"
    )

    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)

    assert errors == []
    assert category_totals == {"Food": 15.5, "Travel": 100.0, "travel": 20.0}
    assert month_totals == {"2024-01": 35.5, "2024-02": 100.0}
    assert month_category_totals == {
        "2024-01": {"Food": 15.5, "travel": 20.0},
        "2024-02": {"Travel": 100.0},
    }


def test_parse_budgets_csv_reads_valid_rows_with_case_insensitive_header():
    csv_text = "Category,LIMIT\n  Food  , 500.00 \nTravel,100\n"

    budgets = parse_budgets_csv(csv_text)

    assert budgets == {"Food": 500.0, "Travel": 100.0}


@pytest.mark.parametrize(
    "csv_text",
    [
        "name,limit\nFood,100\n",
        "category,amount\nFood,100\n",
        "only\nFood,100\n",
    ],
)
def test_parse_budgets_csv_raises_value_error_for_missing_header_columns(csv_text: str):
    with pytest.raises(ValueError):
        parse_budgets_csv(csv_text)


def test_parse_budgets_csv_raises_value_error_for_wrong_column_count_on_data_row():
    csv_text = "category,limit\nFood,100,extra\n"

    with pytest.raises(ValueError):
        parse_budgets_csv(csv_text)


@pytest.mark.parametrize(
    "csv_text",
    [
        "category,limit\n,100\n",
        "category,limit\nFood,0\n",
        "category,limit\nFood,-5\n",
        "category,limit\nFood,not-a-number\n",
    ],
)
def test_parse_budgets_csv_raises_value_error_for_invalid_data_row(csv_text: str):
    with pytest.raises(ValueError):
        parse_budgets_csv(csv_text)


def test_parse_budgets_csv_skips_all_empty_data_rows_without_error():
    csv_text = "category,limit\n   ,   \nFood,25.00\n,\n"

    assert parse_budgets_csv(csv_text) == {"Food": 25.0}


def test_parse_budgets_csv_last_row_wins_for_duplicate_category():
    csv_text = "category,limit\nFood,100\nTravel,50\nFood,200\n"

    assert parse_budgets_csv(csv_text) == {"Food": 200.0, "Travel": 50.0}
