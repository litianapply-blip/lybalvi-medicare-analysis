"""Independent reconciliation of source, SQL models and saved CSV exports."""
import math

import pandas as pd


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_models(con, cleaned, config):
    checks = []
    keys = {'prescriber_product_year': 'year,npi,product', 'prescriber_year': 'year,npi',
            'product_year': 'year,product', 'year_summary': 'year',
            'state_summary': 'year,state', 'segment_year': 'year,state,segment_type,segment'}
    for table, key in keys.items():
        duplicates = con.execute(f'SELECT COUNT(*) FROM (SELECT {key} FROM {table} GROUP BY {key} HAVING COUNT(*) > 1)').fetchone()[0]
        require(duplicates == 0, f'Duplicate reporting keys: {table}')
    checks.append('Source and reporting keys unique')
    require(con.execute('SELECT COUNT(*) FROM prescriber_product_year').fetchone()[0] == len(cleaned), 'Source-to-model row loss')
    for year in config['years']:
        source = cleaned[cleaned.year == year]
        focal = source[source.is_focal]
        row = con.execute('SELECT selected_set_claims, lybalvi_claims, selected_set_observed_prescribers, lybalvi_observed_prescribers, observed_selected_set_share FROM year_summary WHERE year=?', [year]).fetchone()
        expected = (int(source.claims.sum()), int(focal.claims.sum()), source.npi.nunique(), focal.npi.nunique())
        require(tuple(row[:4]) == expected, f'Year total reconciliation failed: {year}')
        require(math.isclose(row[4], expected[1] / expected[0], abs_tol=1e-12), 'Invalid year share denominator')
        for product, rows in source.groupby('product'):
            modeled = con.execute('SELECT claims,observed_prescribers FROM product_year WHERE year=? AND product=?', [year, product]).fetchone()
            require(modeled == (int(rows.claims.sum()), rows.npi.nunique()), 'Product total mismatch')
        for state, state_rows in source.groupby('state'):
            focal_rows = state_rows[state_rows.is_focal]
            actual = con.execute(
                'SELECT selected_set_claims, lybalvi_claims, '
                'selected_set_observed_prescribers, lybalvi_observed_prescribers, '
                'observed_selected_set_share FROM state_summary '
                'WHERE year=? AND state=?', [year, state]
            ).fetchone()
            expected = (
                int(state_rows.claims.sum()),
                int(focal_rows.claims.sum()),
                state_rows.npi.nunique(),
                focal_rows.npi.nunique()
            )
            require(actual is not None, 'Missing state summary')
            require(tuple(actual[:4]) == expected, 'State totals mismatch')
            require(
                math.isclose(actual[4], expected[1] / expected[0], abs_tol=1e-12),
                'State share denominator mismatch'
            )
        for kind, dimension in [('City', 'city'), ('Specialty', 'specialty')]:
            segments = con.execute('SELECT state,segment,selected_set_claims,lybalvi_claims,selected_set_observed_prescribers,lybalvi_observed_prescribers FROM segment_year WHERE year=? AND segment_type=?', [year, kind]).fetchall()
            expected_segments = {}
            for (state, segment), rows in source.groupby(['state', dimension]):
                focal_rows = rows[rows.is_focal]
                expected_segments[(state, f'{segment}, {state}' if kind == 'City' else segment)] = (int(rows.claims.sum()), int(focal_rows.claims.sum()), rows.npi.nunique(), focal_rows.npi.nunique())
            require({(r[0], r[1]): tuple(r[2:]) for r in segments} == expected_segments, f'{kind} reconciliation failed')
    checks.append('Every year/product/city/specialty total and distinct count reconciles to cleaned source')
    for table in ('year_summary', 'segment_year', 'prescriber_year'):
        invalid = con.execute(f'SELECT COUNT(*) FROM {table} WHERE observed_selected_set_share < 0 OR observed_selected_set_share > 1').fetchone()[0]
        require(invalid == 0, f'Invalid shares in {table}')
    checks.append('Shares bounded and aggregate denominators reconciled')
    require(con.execute('SELECT COUNT(*) FROM prescriber_year WHERE NOT lybalvi_record_observed AND lybalvi_claims IS NOT NULL').fetchone()[0] == 0, 'Absent focal record converted to zero')
    require(con.execute('SELECT COUNT(*) FROM prescriber_product_year WHERE beneficiaries IS NULL').fetchone()[0] == int(cleaned.beneficiaries.isna().sum()), 'Missing beneficiary values changed')
    checks.append('Missing focal records and suppressed beneficiary values preserved as NULL')
    if set(config['years']) == {2023, 2024}:
        before = dict(zip(cleaned.loc[cleaned.is_focal & (cleaned.year == 2023), 'npi'], cleaned.loc[cleaned.is_focal & (cleaned.year == 2023), 'claims']))
        after = dict(zip(cleaned.loc[cleaned.is_focal & (cleaned.year == 2024), 'npi'], cleaned.loc[cleaned.is_focal & (cleaned.year == 2024), 'claims']))
        expected = {
            'Continuing observed records': (len(before.keys() & after.keys()), sum(after[n]-before[n] for n in before.keys() & after.keys())),
            'Newly observed records': (len(after.keys()-before.keys()), sum(after[n] for n in after.keys()-before.keys())),
            'No-longer-observed records': (len(before.keys()-after.keys()), -sum(before[n] for n in before.keys()-after.keys()))}
        actual = {r[0]: (r[1], r[2]) for r in con.execute('SELECT cohort,observed_npis,observed_claim_change FROM growth_components').fetchall()}
        require(actual == {k: v for k, v in expected.items() if v[0]}, 'Growth cohort mismatch')
        delta = sum(after.values()) - sum(before.values())
        require(sum(v[1] for v in actual.values()) == delta, 'Growth components do not reconcile')
        require(con.execute('SELECT observed_claim_change FROM year_growth').fetchone()[0] == delta, 'Growth headline mismatch')
        checks.append('Growth cohorts and change independently reconciled by NPI')
    return checks


def validate_exports(con, tableau_dir, tables):
    for table, order in tables.items():
        exported = pd.read_csv(tableau_dir / f'{table}.csv', keep_default_na=False)
        expected = con.execute(f'SELECT * FROM {table} ORDER BY {order}').df()
        require(list(exported.columns) == list(expected.columns), f'CSV schema mismatch: {table}')
        require(len(exported) == len(expected), f'CSV row count mismatch: {table}')
        # Verify each measure/value after round-trip, retaining real blanks as missing.
        for column in expected.columns:
            if pd.api.types.is_numeric_dtype(expected[column]):
                actual = pd.to_numeric(exported[column].replace('', None), errors='raise')
                for x, y in zip(actual, expected[column]):
                    require((pd.isna(x) and pd.isna(y)) or (not pd.isna(x) and not pd.isna(y) and math.isclose(float(x), float(y), rel_tol=1e-12, abs_tol=1e-9)), f'CSV numeric mismatch: {table}.{column}')
            else:
                require(exported[column].astype(str).tolist() == expected[column].astype(str).tolist(), f'CSV value mismatch: {table}.{column}')
    return 'Saved Tableau CSVs reconcile cell-by-cell to ordered SQL outputs'
