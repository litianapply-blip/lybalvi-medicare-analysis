"""Bounded CMS extraction with pinned releases and unchanged, verified caches."""
import hashlib
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from .scope import allowed_states, state_filter_params

CATALOG = 'https://data.cms.gov/data.json'
TITLE = 'Medicare Part D Prescribers - by Provider and Drug'


def digest(content):
    return hashlib.sha256(content).hexdigest()


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def fetch(url, params=None):
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=(10, 60))
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                print(f'Retrying HTTP {response.status_code}: {url}', flush=True)
                time.sleep(2 ** (attempt + 1) + random.random())
                continue
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            print(f'Retrying timed-out request: {url}', flush=True)
            time.sleep(2 ** (attempt + 1) + random.random())
    raise RuntimeError('Retry budget exhausted')


def config_fingerprint(config):
    scope = {k: config[k] for k in ('state', 'years', 'releases', 'products', 'page_size')}
    return digest(json.dumps(scope, sort_keys=True).encode())[:16]


def _verify_page(rows, config, product):
    if not isinstance(rows, list) or len(rows) > config['page_size']:
        raise ValueError('CMS response must be a bounded JSON list')
    for row in rows:
        if row.get('Prscrbr_State_Abrvtn') not in allowed_states(config['state']):
            raise ValueError('CMS state filter was not respected')
        if (row.get('Brnd_Name'), row.get('Gnrc_Name')) != (product['brand'], product['generic']):
            raise ValueError('Unexpected product mapping in API response')
        npi = row.get('Prscrbr_NPI', '')
        if not isinstance(npi, str) or len(npi) != 10 or not npi.isdigit():
            raise ValueError('Invalid prescriber identifier')


def _load_group(folder, config, product):
    manifest = json.loads((folder / 'complete.json').read_text())
    rows = []
    for page in manifest['pages']:
        content = (folder / page['file']).read_bytes()
        if digest(content) != page['sha256']:
            raise ValueError(f'Raw cache checksum mismatch: {folder / page["file"]}')
        data = json.loads(content)
        _verify_page(data, config, product)
        if len(data) != page['rows']:
            raise ValueError('Cached page row-count mismatch')
        rows.extend(data)
    npis = [r['Prscrbr_NPI'] for r in rows]
    if npis != sorted(npis) or len(npis) != len(set(npis)):
        raise ValueError('Duplicate or non-monotonic NPI in exact-product extraction')
    if manifest['pages'][-1]['rows'] != 0 or len(rows) != manifest['total_rows'] or not rows:
        raise ValueError('Extraction lacks terminal empty page or nonempty coverage')
    return rows, manifest


def ingest(root, config, offline=False):
    cache = root / 'data/raw' / ('extract-' + config_fingerprint(config))
    cache.mkdir(parents=True, exist_ok=True)
    catalog_file = cache / 'catalog.json'
    provenance_file = cache / 'catalog_provenance.json'
    if not catalog_file.exists():
        if offline:
            raise ValueError('No cached catalog available for offline run')
        response = fetch(CATALOG)
        response.json()  # Validate JSON before saving an unchanged response.
        catalog_file.write_bytes(response.content)
        save_json(provenance_file, {'url': CATALOG, 'retrieved_utc': utcnow(), 'sha256': digest(response.content)})
    provenance = json.loads(provenance_file.read_text())
    if digest(catalog_file.read_bytes()) != provenance['sha256']:
        raise ValueError('Catalog checksum mismatch')
    catalog = json.loads(catalog_file.read_text())
    records, groups, releases = [], [], []
    for year in config['years']:
        dataset = next(d for d in catalog['dataset'] if
                       d.get('inSeries', [{}])[0].get('title') == TITLE
                       and d['temporal'][0]['startDate'] == f'{year}-01-01'
                       and d['temporal'][0]['endDate'] == f'{year}-12-31')
        release_id = config['releases'][str(year)]
        api = next(d for d in dataset['distribution'] if d.get('format') == 'API'
                   and d['accessURL'].split('/')[-2] == release_id)
        releases.append({'year': year, 'release_id': release_id,
                         'modified': dataset['modified'], 'temporal': dataset['temporal'],
                         'download_url': next(d['downloadURL'] for d in dataset['distribution'] if d.get('format') == 'CSV')})
        for index, product in enumerate(config['products']):
            folder = cache / str(year) / f'product-{index}'
            folder.mkdir(parents=True, exist_ok=True)
            if not (folder / 'complete.json').exists():
                if offline:
                    raise ValueError(f'Incomplete cached extraction: {folder}')
                # Partial files from a failed attempt remain untouched; new attempts get a new folder.
                attempt_dir = folder / ('attempt-' + str(time.time_ns()))
                attempt_dir.mkdir()
                pages, previous_npi, offset = [], None, 0
                for page_number in range(config['max_pages_per_product']):
                    params = {**state_filter_params(config['state']),
                              'filter[Brnd_Name]': product['brand'],
                              'filter[Gnrc_Name]': product['generic'],
                              'sort': 'Prscrbr_NPI', 'size': config['page_size'], 'offset': offset}
                    response = fetch(api['accessURL'], params)
                    rows = response.json()
                    _verify_page(rows, config, product)
                    npis = [r['Prscrbr_NPI'] for r in rows]
                    if npis != sorted(npis) or len(npis) != len(set(npis)):
                        raise ValueError('API did not provide unique NPI ordering')
                    if npis and previous_npi is not None and npis[0] <= previous_npi:
                        raise ValueError('Pagination overlap or unstable ordering')
                    path = attempt_dir / f'page-{page_number:04d}.json'
                    path.write_bytes(response.content)
                    pages.append({'file': str(path.relative_to(folder)), 'sha256': digest(response.content),
                                  'url': response.url, 'retrieved_utc': utcnow(), 'offset': offset,
                                  'rows': len(rows), 'schema': list(rows[0]) if rows else []})
                    print(f'{year} {product["brand"]}: {len(rows)} rows at offset {offset}', flush=True)
                    if not rows:
                        if offset == 0:
                            raise ValueError('Unexpected empty product/year scope; investigate instead of treating as zero')
                        save_json(folder / 'complete.json', {'year': year, 'product': product, 'pages': pages,
                                  'total_rows': offset, 'completeness': 'NPI-sorted disjoint pages through explicit empty terminal page'})
                        break
                    previous_npi = npis[-1]
                    offset += len(rows)
                else:
                    raise ValueError('Page limit reached before end of extraction')
            rows, manifest = _load_group(folder, config, product)
            records.extend(dict(row, service_year=year) for row in rows)
            groups.append(manifest)
    return records, {'catalog': provenance, 'cache_path': str(cache.relative_to(root)),
                     'releases': releases, 'groups': groups, 'total_rows': len(records)}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'config.json').read_text())
    rows, manifest = ingest(root, config)
    save_json(root / 'logs/ingestion_manifest.json', manifest)
    print(f'Complete: {len(rows)} raw records', flush=True)
