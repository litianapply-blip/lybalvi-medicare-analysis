import json
import shutil
from pathlib import Path

import duckdb
import pytest

from src import pipeline
from src.scope import allowed_states, state_filter_params


def test_us_scope():
    states = allowed_states("US")
    assert len(states) == len(set(states)) == 51
    assert "MA" in states and "DC" in states
    assert "PR" not in states
    assert allowed_states("MA") == ["MA"]
    assert state_filter_params("US")[
        "filter[state][condition][operator]"
    ] == "IN"
    with pytest.raises(ValueError):
        allowed_states("INVALID")


def test_separate_states_and_provider_move(tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    config = json.loads((project / "config.json").read_text())
    config["state"] = "US"
    config["products"] = config["products"][:2]
    shutil.copytree(project / "sql", tmp_path / "sql")

    records = []
    for year in (2023, 2024):
        for person, focal_claims in ((1, 20), (2, 30)):
            state = "MA" if person == 1 and year == 2023 else "IL"
            for product in config["products"]:
                claims = focal_claims if product["focal"] else 100
                records.append({
                    "service_year": year,
                    "Prscrbr_NPI": f"{person:010d}",
                    "Prscrbr_City": "SPRINGFIELD",
                    "Prscrbr_State_Abrvtn": state,
                    "Prscrbr_Type": "Synthetic specialty",
                    "Brnd_Name": product["brand"],
                    "Gnrc_Name": product["generic"],
                    "Tot_Clms": str(claims),
                    "Tot_30day_Fills": str(claims),
                    "Tot_Day_Suply": str(claims * 30),
                    "Tot_Drug_Cst": "100.00",
                    "Tot_Benes": "",
                })

    monkeypatch.setattr(
        pipeline, "ingest",
        lambda *args, **kwargs: (records, {"synthetic": True})
    )
    pipeline.run_pipeline(tmp_path, config, offline=True)

    with duckdb.connect(
        str(tmp_path / "data/processed/analytics.duckdb"),
        read_only=True
    ) as con:
        cities = con.execute(
            "SELECT segment FROM segment_year "
            "WHERE year=2023 AND segment_type='City' ORDER BY segment"
        ).fetchall()
        assert cities == [("SPRINGFIELD, IL",), ("SPRINGFIELD, MA",)]

        totals = con.execute(
            "SELECT year,state,lybalvi_claims "
            "FROM state_summary ORDER BY year,state"
        ).fetchall()
        assert totals == [
            (2023, "IL", 30),
            (2023, "MA", 20),
            (2024, "IL", 50),
        ]

        moved = con.execute(
            "SELECT city_changed FROM growth_detail WHERE npi='0000000001'"
        ).fetchone()[0]
        assert moved is True
