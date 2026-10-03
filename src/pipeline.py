"""One-command pipeline: validate a staged bundle, then atomically switch current."""
import argparse
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path

import pandas as pd

from .clean import clean
from .ingest import digest, ingest, save_json, utcnow
from .model import model
from .validate import require, validate_exports, validate_models

BASE_TABLES = {'state_summary': 'year,state', 'year_summary': 'year', 'product_year': 'year,product',
               'segment_year': 'year,state,segment_type,segment',
               'investigation_segments': 'year,state,segment_type,claim_threshold,volume_rank,segment'}
GROWTH_TABLES = {'growth_components': 'cohort', 'year_growth': 'baseline_year',
                 'provider_attribute_changes': 'continuing_selected_set_npis'}


def csv_hashes(folder):
    return {str(p.relative_to(folder)): digest(p.read_bytes()) for p in sorted(folder.rglob('*.csv'))}


def _link(path, target):
    if path.is_symlink():
        if os.readlink(path) != target:
            raise ValueError(f'Unexpected existing link: {path}')
        return
    if path.exists():
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
        else:
            raise ValueError(f'Refusing to replace unmanaged output: {path}')
    path.symlink_to(target)


def promote(root, stage, run_id):
    output = root / 'outputs'
    snapshots = output / 'snapshots'
    snapshots.mkdir(parents=True, exist_ok=True)
    snapshot = snapshots / run_id
    stage.rename(snapshot)
    for name in ('tableau', 'downloads', 'quality_report.json', 'run_manifest.json', 'tableau_data.zip'):
        _link(output / name, 'current/' + name)
    processed = root / 'data/processed'
    processed.mkdir(parents=True, exist_ok=True)
    _link(processed / 'analytics.duckdb', '../../outputs/current/analytics.duckdb')
    current = output / 'current'
    if current.is_symlink():
        previous_temp = output / ('.previous-' + run_id)
        previous_temp.symlink_to(os.readlink(current))
        os.replace(previous_temp, output / 'previous')
    elif current.exists():
        raise ValueError('Refusing to replace unmanaged current output')
    temporary_link = output / ('.current-' + run_id)
    temporary_link.symlink_to('snapshots/' + run_id)
    os.replace(temporary_link, current)  # Entire validated bundle switches in one operation.


def run_pipeline(root, config, offline=False):
    root = Path(root)
    run_id = uuid.uuid4().hex
    started = utcnow()
    stage = root / 'work' / ('stage-' + run_id)
    stage.mkdir(parents=True)
    con = None
    try:
        require(config['years'] in ([2023, 2024], [2024]), 'Supported scopes are 2023/2024 or 2024-only')
        require(sum(p['focal'] for p in config['products']) == 1, 'Exactly one focal product is required')
        require(len({p['product'] for p in config['products']}) == len(config['products']), 'Product labels must be unique')
        records, source = ingest(root, config, offline=offline)
        cleaned, profile = clean(records, config)
        con = model(root, stage, cleaned, config)
        checks = validate_models(con, cleaned, config)
        tables = dict(BASE_TABLES)
        if set(config['years']) == {2023, 2024}:
            tables.update(GROWTH_TABLES)
        tableau = stage / 'tableau'
        tableau.mkdir()
        for table, order in tables.items():
            con.execute(f'SELECT * FROM {table} ORDER BY {order}').df().to_csv(tableau / f'{table}.csv', index=False, lineterminator='\n', na_rep='')
        checks.append(validate_exports(con, tableau, tables))
        downloads = stage / 'downloads'
        downloads.mkdir()
        # Public source identifiers are retained locally; names are not copied to this extract.
        detail_name = config['state'].lower() + '_selected_prescribing_' + '_'.join(map(str, config['years'])) + '.csv'
        cleaned.to_csv(downloads / detail_name, index=False, lineterminator='\n', na_rep='')
        detail = pd.read_csv(downloads / detail_name, dtype={'npi': str}, keep_default_na=False)
        require(len(detail) == len(cleaned) and detail.npi.tolist() == cleaned.npi.tolist(), 'Download row/identifier mismatch')
        require(detail.claims.sum() == cleaned.claims.sum(), 'Download claims mismatch')
        hashes = csv_hashes(stage)
        quality = {'status': 'passed', 'checks': checks, 'profile': profile,
                   'table_rows': {t: con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in tables},
                   'limitations': ['Released records only; missing records are not confirmed zero prescribing.',
                                   'Share denominator is the four explicitly configured products, not the whole market.',
                                   'Formulation is not resolved; this is not an oral-only comparison.',
                                   'Beneficiary counts are never summed into unique patients.']}
        con.close()
        con = None
        save_json(stage / 'quality_report.json', quality)
        save_json(stage / 'run_manifest.json', {'run_id': run_id, 'started_utc': started, 'finished_utc': utcnow(),
                  'status': 'passed', 'offline': offline, 'config': config, 'source': source,
                  'csv_sha256': hashes,
                  'code_sha256': {str(p.relative_to(root)): digest(p.read_bytes()) for pattern in ('src/*.py', 'sql/*.sql', 'requirements.txt') for p in sorted(root.glob(pattern))}})
        with zipfile.ZipFile(stage / 'tableau_data.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for csv in sorted(tableau.glob('*.csv')):
                archive.write(csv, 'tableau/' + csv.name)
            for name in ('metric_dictionary.md', 'tableau_steps.md', 'tableau_reconciliation.md', 'findings.md'):
                document = root / 'docs' / name
                if document.exists():
                    archive.write(document, 'docs/' + name)
        # Logs are written before promotion, so an I/O error cannot falsely mark new outputs as failed.
        save_json(root / 'logs' / (run_id + '.json'), {'run_id': run_id, 'status': 'validated', 'started_utc': started, 'csv_sha256': hashes})
        promote(root, stage, run_id)
        print(f'PASS: {len(cleaned):,} records; {len(tables)} Tableau CSVs; run {run_id}', flush=True)
        return {'run_id': run_id, 'csv_sha256': hashes, 'rows': len(cleaned)}
    except Exception as error:
        if con is not None:
            con.close()
        save_json(root / 'logs' / (run_id + '.json'), {'run_id': run_id, 'status': 'failed', 'started_utc': started,
                  'failed_utc': utcnow(), 'error': f'{type(error).__name__}: {error}', 'outputs_promoted': False})
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--offline', action='store_true', help='Require complete cached sources; make no network calls')
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    run_pipeline(config_path.parent, json.loads(config_path.read_text()), offline=args.offline)


if __name__ == '__main__':
    main()
