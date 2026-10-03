"""Retrieve five real MA LYBALVI records per verified release; not a full extract."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]

def main():
    manifest = {'scope': 'Sample only; incomplete and not suitable for trend estimates', 'requests': []}
    for year in (2023, 2024):
        folder = ROOT / 'data/raw/probe' / str(year)
        metadata = json.loads((folder / 'metadata.json').read_text())
        api = next(d for d in metadata['distribution'] if d.get('format') == 'API' and d.get('description') != 'latest')
        assert metadata['temporal'][0]['startDate'] == f'{year}-01-01'
        params = {'filter[Prscrbr_State_Abrvtn]': 'MA', 'filter[Brnd_Name]': 'Lybalvi', 'size': 5, 'offset': 0}
        response = requests.get(api['accessURL'], params=params, timeout=(10, 45))
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not rows or len(rows) > 5:
            raise ValueError('Unexpected response shape or empty probe')
        required = {'Prscrbr_NPI', 'Prscrbr_State_Abrvtn', 'Brnd_Name', 'Gnrc_Name', 'Tot_Clms'}
        for row in rows:
            assert required <= row.keys()
            assert row['Prscrbr_State_Abrvtn'] == 'MA'
            assert row['Brnd_Name'].lower() == 'lybalvi'
        keys = [(r['Prscrbr_NPI'], r['Brnd_Name'], r['Gnrc_Name']) for r in rows]
        assert len(keys) == len(set(keys)), 'Duplicate candidate key in sample'
        path = folder / 'ma_lybalvi_sample.json'
        if path.exists() and path.read_bytes() != response.content:
            raise RuntimeError('Existing snapshot differs; preserve it before fetching a new version')
        path.write_bytes(response.content)
        entry = {'service_year': year, 'url': response.url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'rows': len(rows), 'sha256': hashlib.sha256(response.content).hexdigest(), 'columns': list(rows[0]), 'path': str(path.relative_to(ROOT)), 'metadata_temporal': metadata['temporal']}
        manifest['requests'].append(entry)
        print(json.dumps({'year': year, 'rows': len(rows), 'first_record': rows[0]}, indent=2))
    (ROOT / 'logs/probe_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    main()
