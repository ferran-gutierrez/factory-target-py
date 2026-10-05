"""compute_top_categories ranking (REQ-1 through REQ-3)."""

from __future__ import annotations

from decimal import Decimal

from factory_target_py.expenses import compute_top_categories


def test_REQ_1_compute_top_categories_orders_by_total_desc_then_category_asc():
    category_totals = {
        "Travel": Decimal("25.00"),
        "Food": Decimal("40.00"),
        "Rent": Decimal("10.00"),
    }

    result = compute_top_categories(category_totals, 2)

    assert len(result) == 2
    assert [entry["category"] for entry in result] == ["Food", "Travel"]
    assert all(set(entry.keys()) == {"category", "total"} for entry in result)
    assert result[0]["total"] == Decimal("40.00")
    assert result[1]["total"] == Decimal("25.00")
    assert all(isinstance(entry["total"], Decimal) for entry in result)


def test_REQ_2_tied_totals_break_by_ascending_category_name():
    category_totals = {
        "Travel": Decimal("15.00"),
        "Food": Decimal("15.00"),
        "Rent": Decimal("40.00"),
    }

    result = compute_top_categories(category_totals, 3)

    assert [entry["category"] for entry in result] == ["Rent", "Food", "Travel"]


def test_REQ_3_n_larger_than_category_count_returns_all_ranked():
    category_totals = {
        "Travel": Decimal("30.00"),
        "Food": Decimal("50.00"),
    }

    result_large_n = compute_top_categories(category_totals, 5)
    result_n_two = compute_top_categories(category_totals, 2)

    assert [entry["category"] for entry in result_large_n] == [
        entry["category"] for entry in result_n_two
    ]
    assert len(result_large_n) == 2
