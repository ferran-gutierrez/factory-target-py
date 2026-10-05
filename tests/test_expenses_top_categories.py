"""Unit tests for compute_top_categories (py-20261005-xj2b REQ-1 through REQ-3)."""

from __future__ import annotations

from decimal import Decimal

from factory_target_py.expenses import compute_top_categories


def test_REQ_1_compute_top_categories_ranks_by_total_desc_then_category_asc():
    category_totals = {
        "Travel": Decimal("20.00"),
        "Food": Decimal("30.00"),
        "Rent": Decimal("30.00"),
    }

    result = compute_top_categories(category_totals, 2)

    assert len(result) == 2
    assert [entry["category"] for entry in result] == ["Food", "Rent"]
    assert result[0]["total"] == Decimal("30.00")
    assert result[1]["total"] == Decimal("30.00")
    for entry in result:
        assert set(entry.keys()) == {"category", "total"}
        assert isinstance(entry["total"], Decimal)


def test_REQ_2_compute_top_categories_tie_break_case_sensitive_lex_order():
    category_totals = {
        "apple": Decimal("10.00"),
        "Banana": Decimal("10.00"),
    }

    result = compute_top_categories(category_totals, 2)

    assert [entry["category"] for entry in result] == ["apple", "Banana"]


def test_REQ_3_compute_top_categories_returns_all_when_n_exceeds_category_count():
    category_totals = {
        "Travel": Decimal("20.00"),
        "Food": Decimal("30.00"),
        "Rent": Decimal("10.00"),
    }

    result = compute_top_categories(category_totals, 10)

    assert len(result) == 3
    assert [entry["category"] for entry in result] == ["Food", "Travel", "Rent"]
