"""Explicit mappings and validation at the verified year/NPI/brand/generic grain."""
import math
from decimal import Decimal, InvalidOperation

import pandas as pd
from .scope import allowed_states

REQUIRED = {'Prscrbr_NPI', 'Prscrbr_City', 'Prscrbr_State_Abrvtn', 'Prscrbr_Type',
            'Brnd_Name', 'Gnrc_Name', 'Tot_Clms', 'Tot_30day_Fills', 'Tot_Day_Suply',
            'Tot_Drug_Cst', 'Tot_Benes', 'service_year'}


def number(value, field, required=False, integer=False):
    if value is None or str(value).strip() == '':
        if required:
            raise ValueError(f'Missing required measure: {field}')
        return None
    try:
        n = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f'Invalid numeric {field}: {value}') from error
    if not n.is_finite() or n < 0:
        raise ValueError(f'Invalid negative or nonfinite {field}: {value}')
    if integer and n != n.to_integral_value():
        raise ValueError(f'Noninteger {field}: {value}')
    return int(n) if integer else float(n)


def clean(records, config):
    if not records:
        raise ValueError('No real records available')
    mapping = {(p['brand'], p['generic']): p for p in config['products']}
    if len(mapping) != len(config['products']):
        raise ValueError('Duplicate configured product pairs')
    output, seen, attributes = [], set(), {}
    for row in records:
        missing = REQUIRED - row.keys()
        if missing:
            raise ValueError(f'Missing required columns: {sorted(missing)}')
        year = row['service_year']
        if year not in config['years'] or row['Prscrbr_State_Abrvtn'] not in allowed_states(config['state']):
            raise ValueError('Unexpected year or state')
        pair = row['Brnd_Name'], row['Gnrc_Name']
        if pair not in mapping:
            raise ValueError(f'Unmapped product: {pair}')
        npi = row['Prscrbr_NPI']
        if not isinstance(npi, str) or len(npi) != 10 or not npi.isdigit():
            raise ValueError('NPI must remain a 10-character string')
        key = year, npi, *pair
        if key in seen:
            raise ValueError(f'Duplicate source key: {key}')
        seen.add(key)
        city = row['Prscrbr_City'].strip().upper() or '(MISSING CITY)'
        specialty = row['Prscrbr_Type'].strip() or '(Missing specialty)'
        prior = attributes.setdefault((year, npi), (row['Prscrbr_State_Abrvtn'], city, specialty))
        if prior != (row['Prscrbr_State_Abrvtn'], city, specialty):
            raise ValueError('Inconsistent provider attributes within year; investigate before aggregation')
        claims = number(row['Tot_Clms'], 'Tot_Clms', required=True, integer=True)
        if claims < 11:
            raise ValueError('Claims violate the verified source publication threshold')
        product = mapping[pair]
        output.append({'year': year, 'npi': npi, 'state': row['Prscrbr_State_Abrvtn'], 'city': city,
                       'specialty': specialty, 'source_city': row['Prscrbr_City'],
                       'source_specialty': row['Prscrbr_Type'], 'source_brand': pair[0],
                       'source_generic': pair[1], 'product': product['product'], 'is_focal': product['focal'],
                       'claims': claims, 'standardized_30day_fills': number(row['Tot_30day_Fills'], 'Tot_30day_Fills'),
                       'days_supply': number(row['Tot_Day_Suply'], 'Tot_Day_Suply', integer=True),
                       'drug_cost': number(row['Tot_Drug_Cst'], 'Tot_Drug_Cst'),
                       'beneficiaries': number(row['Tot_Benes'], 'Tot_Benes', integer=True)})
    df = pd.DataFrame(output).sort_values(['year', 'npi', 'product']).reset_index(drop=True)
    for column in ('days_supply', 'beneficiaries'):
        df[column] = df[column].astype('Int64')
    coverage = {(r['year'], r['product']) for r in output}
    expected = {(y, p['product']) for y in config['years'] for p in config['products']}
    if coverage != expected:
        raise ValueError('Missing product/year coverage')
    profile = {'source_rows': len(records), 'clean_rows': len(df), 'dropped_rows': 0,
               'source_grain': 'service year + NPI + brand + generic',
               'clean_grain': 'year + NPI + configured product',
               'missing_source_values': {key: sum(r.get(key) in ('', None) for r in records)
                                         for key in sorted(REQUIRED)},
               'products': config['products']}
    return df, profile
