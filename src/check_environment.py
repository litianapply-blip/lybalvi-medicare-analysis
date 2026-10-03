"""Verify the isolated environment without downloading or fabricating data."""
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
import pandas
import requests
import duckdb
import pytest

def main():
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Run this check with the project virtual environment.")
    with duckdb.connect(":memory:") as connection:
        result = connection.execute("SELECT 1 + 1 AS setup_check").fetchone()[0]
    if result != 2:
        raise RuntimeError("DuckDB setup check failed.")
    report = {
        "status": "passed",
        "python": platform.python_version(),
        "executable": sys.executable,
        "isolated_environment": True,
        "packages": {name: version(name) for name in ("pandas", "requests", "duckdb", "pytest")},
        "sql": "SELECT 1 + 1 AS setup_check",
        "sql_result": result,
    }
    root = Path(__file__).resolve().parents[1]
    (root / "logs").mkdir(exist_ok=True)
    (root / "logs/environment_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
