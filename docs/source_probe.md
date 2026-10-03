# CMS source probe: passed

Retrieved five real Massachusetts LYBALVI rows for each of service years 2023 and 2024. These are incomplete samples, not analytical exports. Source snapshots are under data/raw/probe; request URLs, timestamps, checksums, column names and counts are in logs/probe_manifest.json.

## Verified releases

- 2023: e54db557-cd82-4e91-a0fe-61aad5865d69
- 2024: d5aa71a8-dcc0-4570-8bcf-bd39deac69fe

The current catalog is https://data.cms.gov/data.json. CMS migrated the catalog to DCAT-US 3.0 on September 29, 2026. Select releases by temporal coverage and pinned distribution URLs, not the moving latest alias. The 2024 title ends in 2024-12-01, but its explicit temporal coverage is January 1 through December 31, 2024 and the source filename identifies DY24.

## Verified API

https://data.cms.gov/api-docs documents exact-match filters, size and offset, and a 5,000-row maximum page size. The probe used filter[Prscrbr_State_Abrvtn]=MA, filter[Brnd_Name]=Lybalvi, size=5 and offset=0. Both responses were JSON lists with 22 fields. Every sampled row passed state and brand checks and candidate-key uniqueness checks. Full pagination and completeness remain untested.

## Definitions and limitations

The current methodology is https://data.cms.gov/sites/default/files/2026-05/MUP_DPR_RY26_20260421_Methodology_508.pdf. The release-linked dictionary is preserved for each year.

- One row represents a prescriber NPI, brand and generic name within a service year. The year comes from release metadata, not a row field.
- Tot_Clms counts claims including original prescriptions and refills. Tot_30day_Fills is a separate standardized measure. Neither represents unique patients or new starts.
- Records with fewer than 11 claims are excluded. Missing records are not confirmed zero activity. Blank beneficiary counts remain missing and are not summed into unique patients.
- Prscrbr_City is provider location. There is no ZIP field in these 22-column responses; city and specialty are the initial segment dimensions.
- Observed brand: Lybalvi. Observed generic: Olanzapine/Samidorphan Malate.
- Numeric values arrive as strings. Preserve NPI as text; parse measures deliberately.
- The source population is Medicare Part D, not the entire prescribing market. Provider demographic timing may differ from service year.

## Repeat this probe

From the project folder: `.venv/bin/python -m src.probe_cms`. This uses the saved verified metadata. Existing differing raw samples are protected from overwrite. The script is a small setup probe, not the full ingestion pipeline.

## Next checkpoint

Verify comparison-product mappings and formulation limitations; implement bounded full extraction with stable pagination and completeness checks. Do not infer trends from these ten sampled rows.
