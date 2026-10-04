"""Mixed valid and invalid expense rows (REQ-10)."""

from decimal import Decimal

from factory_target_py import parse_expense_csv


def _line_numbers(errors) -> list[int]:
    return [err.line if hasattr(err, "line") else err["line"] for err in errors]


def _reasons(errors) -> list[str]:
    return [err.reason if hasattr(err, "reason") else err["reason"] for err in errors]


def test_mixed_rows_aggregate_valid_only_and_collect_distinct_errors():
    """REQ-10: valid rows update totals; invalid rows appear in errors only."""
    csv_text = (
        "date,category,description,amount\n"
        "2024-04-01,Food,Lunch,10.00\n"
        "2024-04-02,Food,,5.00\n"
        "2024-04-03,Travel,Train,20.00\n"
        "not-a-date,Food,Snack,3.00\n"
        "2024-04-05,Office,Paper,0\n"
        "2024-04-06,Food,Dinner,7.50\n"
    )
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {
        "Food": Decimal("17.50"),
        "Travel": Decimal("20.00"),
    }
    assert result.totals_by_month == {
        "2024-04": Decimal("37.50"),
    }

    assert sorted(_line_numbers(result.errors)) == [3, 5, 6]
    reasons = _reasons(result.errors)
    assert len(result.errors) == 3
    assert len(set(_line_numbers(result.errors))) == 3

    assert any("description" in r.lower() for r in reasons)
    assert any("date" in r.lower() for r in reasons)
    assert any("amount" in r.lower() for r in reasons)
