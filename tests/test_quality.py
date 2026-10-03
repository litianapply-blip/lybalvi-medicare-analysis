"""Synthetic fixtures stay in pytest temporary folders, never project exports."""
import copy
import json
import shutil
from pathlib import Path

import duckdb
import pytest

from src import pipeline
from src.clean import clean
from src.ingest import _load_group, digest, save_json

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def example(tmp_path, monkeypatch):
    config = json.loads((PROJECT / 'config.json').read_text())
    config['products'] = config['products'][:2]
    config['threshold_sensitivity'] = [10, 100]
    config['segment_claim_threshold'] = 10
    shutil.copytree(PROJECT / 'sql', tmp_path / 'sql')
    records = []
    def add(year, npi, product, claims):
        records.append({'service_year': year, 'Prscrbr_NPI': npi, 'Prscrbr_City': 'TEST CITY',
                        'Prscrbr_State_Abrvtn': 'MA', 'Prscrbr_Type': 'Synthetic specialty',
                        'Brnd_Name': product['brand'], 'Gnrc_Name': product['generic'],
                        'Tot_Clms': str(claims), 'Tot_30day_Fills': str(claims),
                        'Tot_Day_Suply': str(claims * 30), 'Tot_Drug_Cst': '123.45', 'Tot_Benes': ''})
    focal, comparator = config['products']
    add(2023, '0000000001', focal, 20)
    add(2023, '0000000002', focal, 11)
    add(2024, '0000000001', focal, 30)
    add(2024, '0000000003', focal, 12)
    for year in (2023, 2024):
        for npi in ('0000000001', '0000000002', '0000000003'):
            add(year, npi, comparator, 100)
    monkeypatch.setattr(pipeline, 'ingest', lambda *args, **kwargs: (copy.deepcopy(records), {'synthetic_test_fixture': True}))
    return tmp_path, config, records


def test_growth_missingness_and_repeatability(example):
    root, config, records = example
    first = pipeline.run_pipeline(root, config, offline=True)
    second = pipeline.run_pipeline(root, config, offline=True)
    assert first['csv_sha256'] == second['csv_sha256']
    assert (root / 'outputs/previous').resolve().name == first['run_id']
    with duckdb.connect(str(root / 'data/processed/analytics.duckdb'), read_only=True) as con:
        cohorts = dict(con.execute('SELECT cohort,observed_claim_change FROM growth_components').fetchall())
        assert cohorts == {'Continuing observed records': 10, 'Newly observed records': 12, 'No-longer-observed records': -11}
        assert con.execute('SELECT observed_claim_change FROM year_growth').fetchone()[0] == 11
        assert con.execute("SELECT lybalvi_claims FROM prescriber_year WHERE year=2023 AND npi='0000000003'").fetchone()[0] is None
        assert con.execute('SELECT COUNT(beneficiaries) FROM prescriber_product_year').fetchone()[0] == 0
        assert con.execute('SELECT observed_selected_set_share FROM year_summary WHERE year=2023').fetchone()[0] == pytest.approx(31/331)


@pytest.mark.parametrize('defect,match', [('duplicate', 'Duplicate source key'), ('missing_column', 'Missing required columns'), ('negative', 'negative'), ('unmapped', 'Unmapped product')])
def test_bad_input_keeps_last_good_bundle(example, monkeypatch, defect, match):
    root, config, records = example
    valid = pipeline.run_pipeline(root, config, offline=True)
    pointer = (root / 'outputs/current').resolve()
    broken = copy.deepcopy(records)
    if defect == 'duplicate':
        broken.append(copy.deepcopy(broken[0]))
    elif defect == 'missing_column':
        del broken[0]['Tot_Clms']
    elif defect == 'negative':
        broken[0]['Tot_Clms'] = '-1'
    else:
        broken[0]['Brnd_Name'] = 'Unmapped synthetic product'
    monkeypatch.setattr(pipeline, 'ingest', lambda *args, **kwargs: (broken, {'synthetic_test_fixture': True}))
    with pytest.raises(ValueError, match=match):
        pipeline.run_pipeline(root, config, offline=True)
    assert (root / 'outputs/current').resolve() == pointer
    assert pipeline.csv_hashes(pointer) == valid['csv_sha256']


def test_cached_raw_tampering_is_rejected(tmp_path):
    page = tmp_path / 'page.json'
    page.write_text('[]')
    save_json(tmp_path / 'complete.json', {'pages': [{'file': 'page.json', 'sha256': digest(b'[]'), 'rows': 0}], 'total_rows': 0})
    page.write_text('[{"changed": true}]')
    with pytest.raises(ValueError, match='checksum mismatch'):
        _load_group(tmp_path, {'page_size': 5000}, {})


def test_one_year_scope_omits_growth(example, monkeypatch):
    root, config, records = example
    config['years'] = [2024]
    records = [r for r in records if r['service_year'] == 2024]
    monkeypatch.setattr(pipeline, 'ingest', lambda *args, **kwargs: (records, {'synthetic_test_fixture': True}))
    pipeline.run_pipeline(root, config, offline=True)
    assert not (root / 'outputs/tableau/growth_components.csv').exists()
    assert not (root / 'outputs/tableau/year_growth.csv').exists()
