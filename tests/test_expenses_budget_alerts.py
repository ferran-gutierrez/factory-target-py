"""Budget alerts, month_category_totals, and parse_budgets_csv (REQ-1 through REQ-10)."""

from __future__ import annotations

from decimal import Decimal

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
    assert alert["total"] == Decimal("120.00")
    assert alert["limit"] == Decimal("100.00")
    assert alert["amount_over"] == Decimal("20.00")
    assert isinstance(alert["total"], Decimal)
    assert isinstance(alert["limit"], Decimal)
    assert isinstance(alert["amount_over"], Decimal)


def test_compute_budget_alerts_ignores_categories_absent_from_budgets():
    month_category_totals = {
        "2024-01": {"Food": Decimal("500.00"), "Travel": Decimal("800.00")},
    }
    budgets = {"Food": Decimal("10.00")}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert len(alerts) == 1
    assert alerts[0]["category"] == "Food"


def test_compute_budget_alerts_no_alert_when_total_at_or_under_limit():
    month_category_totals = {
        "2024-01": {"Food": Decimal("100.00")},
        "2024-02": {"Food": Decimal("99.99")},
    }
    budgets = {"Food": Decimal("100.00")}

    assert compute_budget_alerts(month_category_totals, budgets) == []


def test_compute_budget_alerts_missing_inner_category_treated_as_zero_total():
    month_category_totals = {"2024-03": {"Travel": Decimal("50.00")}}
    budgets = {"Food": Decimal("25.00")}

    assert compute_budget_alerts(month_category_totals, budgets) == []


def test_compute_budget_alerts_ordered_by_month_then_category():
    month_category_totals = {
        "2024-02": {"Food": Decimal("50.00")},
        "2024-01": {"Travel": Decimal("40.00"), "Food": Decimal("30.00")},
    }
    budgets = {"Food": Decimal("1.00"), "Travel": Decimal("1.00")}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert [(a["month"], a["category"]) for a in alerts] == [
        ("2024-01", "Food"),
        ("2024-01", "Travel"),
        ("2024-02", "Food"),
    ]

    month_category_totals_ci = {
        "2024-01": {"food": Decimal("15.00"), "Travel": Decimal("15.00")},
    }
    budgets_ci = {"Travel": Decimal("10.00"), "food": Decimal("10.00")}
    alerts_ci = compute_budget_alerts(month_category_totals_ci, budgets_ci)
    assert [a["category"] for a in alerts_ci] == ["food", "Travel"]


def test_REQ_1_compute_budget_alerts_orders_categories_case_insensitively_within_month():
    month_category_totals = {
        "2024-01": {"food": Decimal("15.00"), "Travel": Decimal("15.00")},
    }
    budgets = {"Travel": Decimal("10.00"), "food": Decimal("10.00")}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert [a["category"] for a in alerts] == ["food", "Travel"]


def test_REQ_2_compute_budget_alerts_orders_apple_before_banana_case_insensitive():
    month_category_totals = {
        "2024-05": {"Banana": Decimal("15.00"), "apple": Decimal("15.00")},
    }
    budgets = {"Banana": Decimal("10.00"), "apple": Decimal("10.00")}

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert len(alerts) == 2
    assert alerts[0]["category"] == "apple"
    assert alerts[1]["category"] == "Banana"


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
    assert category_totals == {
        "Food": Decimal("15.50"),
        "Travel": Decimal("120.00"),
    }
    assert month_totals == {
        "2024-01": Decimal("35.50"),
        "2024-02": Decimal("100.00"),
    }
    assert month_category_totals == {
        "2024-01": {"Food": Decimal("15.50"), "Travel": Decimal("20.00")},
        "2024-02": {"Travel": Decimal("100.00")},
    }
    for month_map in month_category_totals.values():
        for value in month_map.values():
            assert isinstance(value, Decimal)


def test_parse_budgets_csv_reads_valid_rows_with_case_insensitive_header():
    csv_text = "Category,LIMIT\n  Food  , 500.00 \nTravel,100\n"

    budgets = parse_budgets_csv(csv_text)

    assert budgets == {"Food": Decimal("500.00"), "Travel": Decimal("100.00")}
    assert all(isinstance(limit, Decimal) for limit in budgets.values())


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

    budgets = parse_budgets_csv(csv_text)
    assert budgets == {"Food": Decimal("25.00")}
    assert isinstance(budgets["Food"], Decimal)


def test_parse_budgets_csv_last_row_wins_for_duplicate_category():
    csv_text = "category,limit\nFood,100\nTravel,50\nFood,200\n"

    with pytest.raises(ValueError, match="duplicate category"):
        parse_budgets_csv(csv_text)


def test_REQ_3_compute_budget_alerts_matches_budget_category_case_insensitively():
    month_category_totals = {"2024-05": {"Food": Decimal("15.00")}}
    budgets = parse_budgets_csv("category,limit\n FOOD ,10.00\n")

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["category"] == "Food"
    assert alert["limit"] == Decimal("10.00")
    assert alert["amount_over"] == Decimal("5.00")
    assert alert["total"] == Decimal("15.00")
    assert alert["month"] == "2024-05"


@pytest.mark.parametrize(
    "csv_text",
    [
        "category,limit\nFood,100\nFOOD,200\n",
        "category,limit\n  Food  ,100\nFood,200\n",
    ],
)
def test_REQ_4_parse_budgets_csv_raises_duplicate_category(csv_text: str):
    with pytest.raises(ValueError, match="duplicate category"):
        parse_budgets_csv(csv_text)


def test_compute_budget_alerts_amount_over_exact_decimal_for_small_fractions():
    expense_csv = (
        "date,category,description,amount\n2024-03-01,Food,A,0.10\n2024-03-02,Food,B,0.20\n"
    )
    budget_csv = "category,limit\nFood,0.10\n"

    _, _, month_category_totals, errors = import_expenses(expense_csv)
    assert errors == []
    budgets = parse_budgets_csv(budget_csv)

    alerts = compute_budget_alerts(month_category_totals, budgets)

    assert len(alerts) == 1
    assert alerts[0]["amount_over"] == Decimal("0.20")
    assert isinstance(alerts[0]["amount_over"], Decimal)
