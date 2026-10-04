"""Tests for parse_expense_csv (REQ-1 through REQ-9)."""

from decimal import Decimal

import pytest

from factory_target_py import parse_expense_csv


def _line_numbers(errors) -> list[int]:
    return [err.line if hasattr(err, "line") else err["line"] for err in errors]


def _reasons(errors) -> list[str]:
    return [err.reason if hasattr(err, "reason") else err["reason"] for err in errors]


def test_result_exposes_totals_and_errors():
    """REQ-1: result has totals_by_category, totals_by_month, and errors."""
    csv_text = "date,category,description,amount\n2024-03-01,Travel,Flight,125.50\n"
    result = parse_expense_csv(csv_text)

    assert hasattr(result, "totals_by_category")
    assert hasattr(result, "totals_by_month")
    assert hasattr(result, "errors")

    assert result.totals_by_category["Travel"] == Decimal("125.50")
    assert result.totals_by_month["2024-03"] == Decimal("125.50")
    assert result.errors == []


def test_case_insensitive_header_and_extra_columns_ignored():
    """REQ-2: header columns matched case-insensitively; extra columns ignored."""
    csv_text = "DATE,CATEGORY,DESCRIPTION,AMOUNT,notes\n2024-01-10,Food,Lunch,12.00,ignore me\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category["Food"] == Decimal("12.00")
    assert result.errors == []


def test_valid_row_requires_trimmed_non_empty_fields_and_positive_amount():
    """REQ-3: valid rows after trim with real date and amount > 0."""
    csv_text = "date,category,description,amount\n2024-06-15,  Office  ,  Supplies  ,  3.25  \n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category["Office"] == Decimal("3.25")
    assert result.totals_by_month["2024-06"] == Decimal("3.25")
    assert result.errors == []


def test_valid_rows_aggregate_by_trimmed_category_and_month():
    """REQ-4: amounts sum into category and YYYY-MM month buckets."""
    csv_text = (
        "date,category,description,amount\n"
        "2024-02-01,Food,Breakfast,10.00\n"
        "2024-02-20, Food ,Dinner,5.50\n"
        "2024-03-01,Travel,Hotel,100.00\n"
    )
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {
        "Food": Decimal("15.50"),
        "Travel": Decimal("100.00"),
    }
    assert result.totals_by_month == {
        "2024-02": Decimal("15.50"),
        "2024-03": Decimal("100.00"),
    }
    assert result.errors == []


@pytest.mark.parametrize(
    ("csv_row", "physical_line"),
    [
        ("2024-13-01,Food,Lunch,10.00", 2),
        ("not-a-date,Food,Lunch,10.00", 2),
        (" ,Food,Lunch,10.00", 2),
        ("2024-02-30,Food,Lunch,10.00", 2),
    ],
)
def test_invalid_date_produces_line_specific_error(csv_row, physical_line):
    """REQ-5: bad dates are skipped with line number and date-related reason."""
    csv_text = "date,category,description,amount\n" + csv_row + "\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {}
    assert result.totals_by_month == {}
    assert physical_line in _line_numbers(result.errors)
    matching = [
        r
        for e, r in zip(result.errors, _reasons(result.errors), strict=True)
        if (e.line if hasattr(e, "line") else e["line"]) == physical_line
    ]
    assert matching
    assert "date" in matching[0].lower()


@pytest.mark.parametrize(
    ("csv_row", "field_hint"),
    [
        ("2024-01-01,,Lunch,10.00", "category"),
        ("2024-01-01,Food,,10.00", "description"),
        ("2024-01-01,   ,Lunch,10.00", "category"),
    ],
)
def test_empty_category_or_description_produces_error(csv_row, field_hint):
    """REQ-6: blank category or description yields line error naming the field."""
    csv_text = "date,category,description,amount\n" + csv_row + "\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {}
    assert _line_numbers(result.errors) == [2]
    reason = _reasons(result.errors)[0].lower()
    assert field_hint in reason


@pytest.mark.parametrize(
    "csv_row",
    [
        "2024-01-01,Food,Lunch,",
        "2024-01-01,Food,Lunch,0",
        "2024-01-01,Food,Lunch,-1.00",
        "2024-01-01,Food,Lunch,abc",
        "2024-01-01,Food,Lunch,   ",
    ],
)
def test_invalid_amount_produces_line_specific_error(csv_row):
    """REQ-7: bad amounts are skipped with amount-related reason."""
    csv_text = "date,category,description,amount\n" + csv_row + "\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {}
    assert _line_numbers(result.errors) == [2]
    assert "amount" in _reasons(result.errors)[0].lower()


def test_missing_or_malformed_columns_produce_column_error():
    """REQ-8: rows missing required columns produce column-related errors."""
    csv_text = "date,category,description,amount\n2024-01-01,Food\n2024-01-02\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {}
    assert sorted(_line_numbers(result.errors)) == [2, 3]
    for reason in _reasons(result.errors):
        lowered = reason.lower()
        assert "column" in lowered or "missing" in lowered or "invalid" in lowered


def test_header_only_yields_empty_totals_and_errors():
    """REQ-9: valid header with no data rows."""
    csv_text = "date,category,description,amount\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {}
    assert result.totals_by_month == {}
    assert result.errors == []


def test_blank_lines_do_not_create_errors_but_preserve_physical_line_numbers():
    """Assumption: blank lines ignored; error line numbers match physical lines."""
    csv_text = "date,category,description,amount\n\nbad-date,Food,Lunch,10.00\n"
    result = parse_expense_csv(csv_text)

    assert result.totals_by_category == {}
    assert _line_numbers(result.errors) == [3]
    assert "date" in _reasons(result.errors)[0].lower()
