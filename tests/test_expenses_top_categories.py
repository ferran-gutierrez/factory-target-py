"""compute_top_categories (py-20261005-wa2k REQ-1 through REQ-3)."""

from __future__ import annotations

from decimal import Decimal

from factory_target_py.expenses import compute_top_categories


def test_REQ_1_rank_by_desc_total_then_asc_category_lexicographic():
    category_totals = {
        "Travel": Decimal("50.00"),
        "Food": Decimal("30.00"),
        "Rent": Decimal("50.00"),
    }

    result = compute_top_categories(category_totals, 2)

    assert len(result) == 2
    assert [entry["category"] for entry in result] == ["Rent", "Travel"]
    assert result[0]["total"] == Decimal("50.00")
    assert result[1]["total"] == Decimal("50.00")
    assert all(set(entry.keys()) == {"category", "total"} for entry in result)
    assert all(isinstance(entry["category"], str) for entry in result)
    assert all(isinstance(entry["total"], Decimal) for entry in result)


def test_REQ_2_returns_all_categories_ordered_when_n_is_large_enough():
    category_totals = {
        "Travel": Decimal("50.00"),
        "Food": Decimal("30.00"),
        "Rent": Decimal("50.00"),
    }

    result = compute_top_categories(category_totals, 10)

    assert len(result) == 3
    assert [entry["category"] for entry in result] == ["Rent", "Travel", "Food"]
    assert [entry["total"] for entry in result] == [
        Decimal("50.00"),
        Decimal("50.00"),
        Decimal("30.00"),
    ]


def test_REQ_3_empty_category_totals_returns_empty_list():
    assert compute_top_categories({}, 1) == []
    assert compute_top_categories({}, 100) == []
