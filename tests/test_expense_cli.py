import json
import subprocess
import sys
from pathlib import Path

HEADER = "date,category,description,amount\n"


def test_req11_module_cli_reads_utf8_and_prints_json(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        HEADER + "2024-04-10,food,café,10.50\n" + "2024-04-11,travel,ride,20\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-m", "factory_target_py", str(csv_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)

    assert payload["by_category"] == {"food": "10.50", "travel": "20"}
    assert payload["by_month"] == {"2024-04": "30.50"}
    assert payload["errors"] == []


def test_req11_cli_json_includes_errors_unchanged(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        HEADER + "2024-05-01,food,lunch,5.00\n" + "2024-05-02,,no category,1.00\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "-m", "factory_target_py", str(csv_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)

    assert payload["by_category"] == {"food": "5.00"}
    assert payload["by_month"] == {"2024-05": "5.00"}
    assert payload["errors"] == [{"line": 3, "reason": "empty category"}]
