"""compute_top_categories (REQ-1 through REQ-5)."""

from __future__ import annotations

from decimal import Decimal

from factory_target_py.expenses import compute_top_categories


def test_REQ_1_compute_top_categories_returns_at_most_n_ordered_entries():
    category_totals = {
        "Zebra": Decimal("30.00"),
        "Alpha": Decimal("100.00"),
        "Middle": Decimal("50.00"),
        "Beta": Decimal("100.00"),
    }

    result = compute_top_categories(category_totals, 3)

    assert len(result) == 3
    for entry in result:
        assert set(entry.keys()) == {"category", "total"}
        assert isinstance(entry["category"], str)
        assert isinstance(entry["total"], Decimal)

    assert [entry["category"] for entry in result] == ["Alpha", "Beta", "Middle"]
    assert [entry["total"] for entry in result] == [
        Decimal("100.00"),
        Decimal("100.00"),
        Decimal("50.00"),
    ]


def test_REQ_2_compute_top_categories_picks_highest_totals_up_to_n():
    category_totals = {
        "Travel": Decimal("50.00"),
        "Food": Decimal("100.00"),
        "Rent": Decimal("75.00"),
    }

    result = compute_top_categories(category_totals, 2)

    assert [entry["category"] for entry in result] == ["Food", "Rent"]
    assert [entry["total"] for entry in result] == [
        Decimal("100.00"),
        Decimal("75.00"),
    ]


def test_REQ_3_compute_top_categories_tie_breaks_categories_case_insensitively():
    category_totals = {
        "Banana": Decimal("10.00"),
        "apple": Decimal("10.00"),
    }

    result = compute_top_categories(category_totals, 2)

    assert len(result) == 2
    assert result[0]["category"] == "apple"
    assert result[1]["category"] == "Banana"
    assert result[0]["total"] == Decimal("10.00")
    assert result[1]["total"] == Decimal("10.00")


def test_REQ_4_compute_top_categories_returns_all_when_n_exceeds_key_count():
    category_totals = {
        "Rent": Decimal("75.00"),
        "Food": Decimal("100.00"),
        "Travel": Decimal("50.00"),
    }

    result_all = compute_top_categories(category_totals, 3)
    result_large_n = compute_top_categories(category_totals, 10)

    assert [entry["category"] for entry in result_all] == ["Food", "Rent", "Travel"]
    assert result_large_n == result_all


def test_REQ_5_compute_top_categories_empty_input_returns_empty_list():
    assert compute_top_categories({}, 5) == []
