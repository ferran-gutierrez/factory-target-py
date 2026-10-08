"""Tests for import_expenses (REQ-1 through REQ-11)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from factory_target_py.expenses import import_expenses


def _errors_by_line(errors: list[dict]) -> dict[int, str]:
    return {entry["line"]: entry["reason"] for entry in errors}


def _assert_all_totals_are_decimal(
    category_totals: dict[str, Decimal],
    month_totals: dict[str, Decimal],
    month_category_totals: dict[str, dict[str, Decimal]] | None = None,
) -> None:
    for value in category_totals.values():
        assert isinstance(value, Decimal)
    for value in month_totals.values():
        assert isinstance(value, Decimal)
    if month_category_totals is not None:
        for by_category in month_category_totals.values():
            for value in by_category.values():
                assert isinstance(value, Decimal)


def test_import_returns_tuple_with_expected_keys_and_shapes():
    csv_text = "date,category,description,amount\n"
    category_totals, month_totals, _, errors = import_expenses(csv_text)
    assert isinstance(category_totals, dict)
    assert isinstance(month_totals, dict)
    assert isinstance(errors, list)
    assert category_totals == {}
    assert month_totals == {}
    assert errors == []


def test_error_records_have_line_and_reason():
    csv_text = "date,category,description,amount\n2024-01-01,Food,Lunch,not-a-number\n"
    _, _, _, errors = import_expenses(csv_text)
    assert len(errors) == 1
    assert set(errors[0].keys()) == {"line", "reason"}
    assert errors[0]["line"] == 2
    assert errors[0]["reason"] == "invalid amount"


def test_header_is_case_insensitive_and_not_counted_as_data():
    csv_text = "DATE,Category,DESCRIPTION,AMOUNT\n2024-06-10,Food,Meal,9.25\n"
    category_totals, month_totals, _, errors = import_expenses(csv_text)
    assert errors == []
    assert category_totals == {"Food": Decimal("9.25")}
    assert month_totals == {"2024-06": Decimal("9.25")}
    _assert_all_totals_are_decimal(category_totals, month_totals)


def test_wrong_number_of_columns_records_error_with_line_number():
    csv_text = "date,category,description,amount\n2024-01-01,Food\n2024-01-02,a,b,c,d,extra\n"
    _, _, _, errors = import_expenses(csv_text)
    by_line = _errors_by_line(errors)
    assert by_line[2] == "wrong number of columns"
    assert by_line[3] == "wrong number of columns"


def test_fields_are_stripped_before_validation():
    csv_text = "date,category,description,amount\n  2024-01-05  ,  Travel  ,  Taxi  ,  15.00  \n"
    category_totals, month_totals, _, errors = import_expenses(csv_text)
    assert errors == []
    assert category_totals == {"Travel": Decimal("15.00")}
    assert month_totals == {"2024-01": Decimal("15.00")}
    _assert_all_totals_are_decimal(category_totals, month_totals)


def test_all_empty_fields_after_strip_skipped_without_error():
    csv_text = "date,category,description,amount\n   ,   ,   ,   \n,,,\n"
    category_totals, month_totals, _, errors = import_expenses(csv_text)
    assert category_totals == {}
    assert month_totals == {}
    assert errors == []


def test_invalid_date_format():
    csv_text = "date,category,description,amount\n01-01-2024,Food,Lunch,5.00\n"
    _, _, _, errors = import_expenses(csv_text)
    assert _errors_by_line(errors)[2] == "invalid date"


def test_invalid_calendar_date():
    csv_text = "date,category,description,amount\n2024-02-30,Food,Lunch,5.00\n"
    _, _, _, errors = import_expenses(csv_text)
    assert _errors_by_line(errors)[2] == "invalid date"


def test_empty_category_after_strip():
    csv_text = "date,category,description,amount\n2024-01-01,   ,Lunch,5.00\n"
    _, _, _, errors = import_expenses(csv_text)
    assert _errors_by_line(errors)[2] == "empty category"


def test_empty_description_after_strip():
    csv_text = "date,category,description,amount\n2024-01-01,Food,  ,5.00\n"
    _, _, _, errors = import_expenses(csv_text)
    assert _errors_by_line(errors)[2] == "empty description"


@pytest.mark.parametrize(
    "amount_field",
    [
        "0",
        "0.00",
        "-1",
        "-0.01",
        "not-a-number",
        "12.34.56",
    ],
)
def test_invalid_amount(amount_field: str):
    csv_text = f"date,category,description,amount\n2024-01-01,Food,Lunch,{amount_field}\n"
    _, _, _, errors = import_expenses(csv_text)
    assert _errors_by_line(errors)[2] == "invalid amount"


def test_multiple_validation_failures_record_only_first_in_order():
    csv_text = "date,category,description,amount\nbad-date,   ,  ,not-a-number\n"
    _, _, _, errors = import_expenses(csv_text)
    assert len(errors) == 1
    assert errors[0]["line"] == 2
    assert errors[0]["reason"] == "invalid date"


def test_category_with_invalid_date_still_reports_date_first():
    csv_text = "date,category,description,amount\n2024-13-01,Food,Lunch,-5\n"
    _, _, _, errors = import_expenses(csv_text)
    assert len(errors) == 1
    assert errors[0]["reason"] == "invalid date"


def test_empty_category_before_empty_description_and_amount():
    csv_text = "date,category,description,amount\n2024-01-01,,,0\n"
    _, _, _, errors = import_expenses(csv_text)
    assert len(errors) == 1
    assert errors[0]["reason"] == "empty category"


def test_empty_description_before_invalid_amount():
    csv_text = "date,category,description,amount\n2024-01-01,Food,,0\n"
    _, _, _, errors = import_expenses(csv_text)
    assert len(errors) == 1
    assert errors[0]["reason"] == "empty description"


def test_valid_rows_aggregate_by_category_and_month():
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
    _assert_all_totals_are_decimal(category_totals, month_totals, month_category_totals)


def test_REQ_1_case_insensitive_categories_merge_under_first_row_spelling():
    csv_text = "date,category,description,amount\n2024-06-01, Food,Lunch,4.00\n2024-06-02,FOOD ,Dinner,6.00\n"
    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)
    assert errors == []
    assert set(category_totals.keys()) == {"Food"}
    assert category_totals["Food"] == Decimal("10.00")
    assert "FOOD" not in category_totals
    assert month_category_totals["2024-06"] == {"Food": Decimal("10.00")}
    assert month_totals["2024-06"] == Decimal("10.00")
    _assert_all_totals_are_decimal(category_totals, month_totals, month_category_totals)


def test_REQ_2_same_month_travel_variants_merge_under_first_canonical_key():
    csv_text = "date,category,description,amount\n2024-05-10,travel,Leg1,1.00\n2024-05-11, Travel,Leg2,2.00\n2024-05-12,TRAVEL,Leg3,3.00\n"
    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)
    assert errors == []
    assert category_totals == {"travel": Decimal("6.00")}
    assert "Travel" not in category_totals
    assert "TRAVEL" not in category_totals
    assert month_category_totals["2024-05"] == {"travel": Decimal("6.00")}
    assert month_totals["2024-05"] == Decimal("6.00")
    _assert_all_totals_are_decimal(category_totals, month_totals, month_category_totals)


def test_totals_equal_mathematical_sum_of_parsed_amounts():
    csv_text = "date,category,description,amount\n2024-03-01,Food,A,0.10\n2024-03-02,Food,B,0.20\n2024-03-03,Food,C,0.30\n"
    category_totals, month_totals, _, errors = import_expenses(csv_text)
    assert errors == []
    assert category_totals["Food"] == Decimal("0.60")
    assert month_totals["2024-03"] == Decimal("0.60")
    _assert_all_totals_are_decimal(category_totals, month_totals)


def test_import_accumulates_category_total_with_decimal_not_float():
    csv_text = "date,category,description,amount\n2024-03-01,Food,A,0.10\n2024-03-02,Food,B,0.20\n"
    category_totals, month_totals, month_category_totals, errors = import_expenses(csv_text)
    assert errors == []
    assert category_totals["Food"] == Decimal("0.30")
    assert category_totals["Food"] != 0.30000000000000004
    assert isinstance(category_totals["Food"], Decimal)
    assert month_totals["2024-03"] == Decimal("0.30")
    assert month_category_totals["2024-03"]["Food"] == Decimal("0.30")
    _assert_all_totals_are_decimal(category_totals, month_totals, month_category_totals)


def test_quoted_csv_fields_parsed_with_standard_csv_rules():
    csv_text = 'date,category,description,amount\n2024-04-01,Food,"Lunch, special",12.00\n'
    category_totals, month_totals, _, errors = import_expenses(csv_text)
    assert errors == []
    assert category_totals == {"Food": Decimal("12.00")}
    _assert_all_totals_are_decimal(category_totals, month_totals)
