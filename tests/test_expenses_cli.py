"""CLI for python -m factory_target_py.expenses (REQ-13, REQ-14)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_expenses_module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "factory_target_py.expenses", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_reads_file_and_prints_json_result(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Food,Dinner,4.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"category_totals", "month_totals", "errors"}
    assert payload["category_totals"] == {"Food": 12.0}
    assert payload["month_totals"] == {"2024-05": 12.0}
    assert payload["errors"] == []


def test_cli_json_error_objects_use_line_and_reason_keys(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,,Snack,3.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["errors"]) == 1
    assert set(payload["errors"][0].keys()) == {"line", "reason"}
    assert payload["errors"][0]["line"] == 2
    assert payload["errors"][0]["reason"] == "empty category"


def test_cli_wrong_argument_count_writes_usage_to_stderr_and_exits_nonzero():
    no_args = _run_expenses_module()
    assert no_args.returncode != 0
    assert "usage" in no_args.stderr.lower()

    too_many = _run_expenses_module("a.csv", "b.csv")
    assert too_many.returncode != 0
    assert "usage" in too_many.stderr.lower()
