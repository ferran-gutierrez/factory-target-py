from decimal import Decimal

import pytest

from factory_target_py.expense_importer import import_expenses

HEADER = "date,category,description,amount\n"


def test_req1_return_structure_and_types():
    csv_text = HEADER + "2024-03-15,travel,flight,120.50\n"
    result = import_expenses(csv_text)

    assert set(result.keys()) == {"by_category", "by_month", "errors"}
    assert isinstance(result["by_category"], dict)
    assert isinstance(result["by_month"], dict)
    assert isinstance(result["errors"], list)

    assert result["by_category"]["travel"] == Decimal("120.50")
    assert result["by_month"]["2024-03"] == Decimal("120.50")
    assert result["errors"] == []


def test_req2_header_row_skipped_not_validated_or_aggregated():
    csv_text = "not-a-date,,,\n2024-01-10,food,lunch,9.99\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {"food": Decimal("9.99")}
    assert result["by_month"] == {"2024-01": Decimal("9.99")}
    assert result["errors"] == []


def test_req3_wrong_column_count_produces_error():
    csv_text = HEADER + "2024-01-01,food,only-three-fields\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {}
    assert result["by_month"] == {}
    assert result["errors"] == [{"line": 2, "reason": "wrong column count"}]


def test_req3_csv_quoting_parses_four_fields_with_commas_in_description():
    csv_text = HEADER + '2024-06-01,food,"burger, fries",12.00\n'
    result = import_expenses(csv_text)

    assert result["by_category"] == {"food": Decimal("12.00")}
    assert result["errors"] == []


def test_req4_invalid_date_after_trim():
    csv_text = HEADER + "2024-02-30,food,dinner,20.00\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {}
    assert result["errors"] == [{"line": 2, "reason": "invalid date"}]


def test_req4_invalid_date_format():
    csv_text = HEADER + "01/15/2024,food,dinner,20.00\n"
    result = import_expenses(csv_text)

    assert result["errors"] == [{"line": 2, "reason": "invalid date"}]


def test_req4_date_whitespace_trimmed_before_validation():
    csv_text = HEADER + "  2024-05-01  ,food,lunch,5.00\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {"food": Decimal("5.00")}
    assert result["by_month"] == {"2024-05": Decimal("5.00")}
    assert result["errors"] == []


def test_req5_empty_category_after_trim():
    csv_text = HEADER + "2024-01-01,  ,desc,10.00\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {}
    assert result["errors"] == [{"line": 2, "reason": "empty category"}]


def test_req6_empty_description_after_trim():
    csv_text = HEADER + "2024-01-01,food,  ,10.00\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {}
    assert result["errors"] == [{"line": 2, "reason": "empty description"}]


@pytest.mark.parametrize(
    "amount",
    ["", "  ", "abc", "0", "0.00", "-1.50", "-0.01"],
)
def test_req7_invalid_amount_not_positive_decimal(amount):
    csv_text = HEADER + f"2024-01-01,food,lunch,{amount}\n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {}
    assert result["errors"] == [{"line": 2, "reason": "invalid amount"}]


def test_req7_valid_positive_amount_with_whitespace_trim():
    csv_text = HEADER + "2024-01-01,food,lunch,  15.25  \n"
    result = import_expenses(csv_text)

    assert result["by_category"] == {"food": Decimal("15.25")}
    assert result["errors"] == []


def test_req8_line_numbers_are_one_based_physical_lines():
    csv_text = (
        HEADER
        + "2024-01-01,food,lunch,10.00\n"
        + "\n"
        + "bad-row\n"
        + "2024-01-02,food,dinner,5.00\n"
    )
    result = import_expenses(csv_text)

    assert result["by_category"] == {"food": Decimal("15.00")}
    assert result["errors"] == [{"line": 4, "reason": "wrong column count"}]


def test_req9_accumulates_by_category_and_by_month():
    csv_text = (
        HEADER
        + "2024-01-05,food,breakfast,4.00\n"
        + "2024-01-20,food,dinner,16.00\n"
        + "2024-02-01,travel,train,50.00\n"
        + "2024-02-10,travel,taxi,25.50\n"
    )
    result = import_expenses(csv_text)

    assert result["by_category"] == {
        "food": Decimal("20.00"),
        "travel": Decimal("75.50"),
    }
    assert result["by_month"] == {
        "2024-01": Decimal("20.00"),
        "2024-02": Decimal("75.50"),
    }
    assert result["errors"] == []


def test_req10_mixed_valid_and_invalid_rows():
    csv_text = (
        HEADER
        + "2024-03-01,food,lunch,10.00\n"
        + "2024-03-02,,missing category,5.00\n"
        + "2024-03-03,travel,,8.00\n"
        + "not-a-date,food,bad date row,3.00\n"
        + "2024-03-05,food,extra,field,too many\n"
        + "2024-03-06,food,dinner,0\n"
        + "2024-03-07,food,valid,7.50\n"
    )
    result = import_expenses(csv_text)

    assert result["by_category"] == {"food": Decimal("17.50")}
    assert result["by_month"] == {"2024-03": Decimal("17.50")}
    assert sorted(result["errors"], key=lambda e: e["line"]) == [
        {"line": 3, "reason": "empty category"},
        {"line": 4, "reason": "empty description"},
        {"line": 5, "reason": "invalid date"},
        {"line": 6, "reason": "wrong column count"},
        {"line": 7, "reason": "invalid amount"},
    ]


def test_empty_file_yields_empty_aggregates_and_errors():
    result = import_expenses("")

    assert result["by_category"] == {}
    assert result["by_month"] == {}
    assert result["errors"] == []


def test_header_only_yields_empty_aggregates_and_errors():
    result = import_expenses(HEADER)

    assert result["by_category"] == {}
    assert result["by_month"] == {}
    assert result["errors"] == []
