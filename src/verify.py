"""Prove real-input repeatability and failure isolation without changing raw data."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

from . import pipeline
from .ingest import ingest, save_json, utcnow


def main():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'config.json').read_text())
    first = pipeline.run_pipeline(root, config, offline=True)
    second = pipeline.run_pipeline(root, config, offline=True)
    if first['csv_sha256'] != second['csv_sha256']:
        raise ValueError('Real cached-input reruns produced different CSV outputs')
    records, source = ingest(root, config, offline=True)
    pointer = (root / 'outputs/current').resolve()
    failures = []
    for defect, expected in [('duplicate', 'Duplicate source key'), ('missing_column', 'Missing required columns'), ('negative_claims', 'negative')]:
        changed = copy.deepcopy(records)
        if defect == 'duplicate':
            changed.append(copy.deepcopy(changed[0]))
        elif defect == 'missing_column':
            del changed[0]['Tot_Clms']
        else:
            changed[0]['Tot_Clms'] = '-1'
        try:
            # Only the in-memory input is altered; cached real records remain unchanged.
            with patch.object(pipeline, 'ingest', return_value=(changed, source)):
                pipeline.run_pipeline(root, config, offline=True)
        except ValueError as error:
            if expected not in str(error):
                raise
            message = str(error)
        else:
            raise ValueError(f'Invalid input was accepted: {defect}')
        if (root / 'outputs/current').resolve() != pointer:
            raise ValueError('A failed run changed the current snapshot pointer')
        if pipeline.csv_hashes(pointer) != second['csv_sha256']:
            raise ValueError('A failed run changed last-good CSV contents')
        failures.append({'defect': defect, 'rejected_with': message,
                         'current_pointer_unchanged': True, 'csv_hashes_unchanged': True})
    result = {'status': 'passed', 'verified_utc': utcnow(), 'real_rows': len(records),
              'first_run_id': first['run_id'], 'second_run_id': second['run_id'],
              'cached_rerun_identical': True, 'csv_sha256': second['csv_sha256'],
              'controlled_failures': failures}
    save_json(root / 'logs/verification_summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
