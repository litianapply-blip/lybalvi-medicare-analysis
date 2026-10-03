# LYBALVI Medicare Part D prescribing analysis

Independent portfolio project by [Li Tian, PhD](https://www.linkedin.com/in/li-tian-phd-34428524). Not affiliated with or sponsored by Alkermes.

**[Explore the Tableau dashboard](https://public.tableau.com/views/LYBALVIMedicarePartDAnalysisWorkinProgress/LYBALVIPrescribingOverview)** · **[Read the two-page report](reports/LYBALVI_Medicare_Part_D_Analysis.pdf)**

## Business question

How did observed LYBALVI claims change between 2023 and 2024, and what contributed to that change?

## Key findings

- Observed claims increased **45.9%**, from **39,134 to 57,090**.
- Continuing observed prescribers contributed **+5,906** claims; newly observed records contributed **+19,727**; no-longer-observed records contributed **-7,677**.
- LYBALVI share within the explicitly selected four-product set increased from **0.274% to 0.382%**. This is not total market share.

CMS suppresses provider-drug records with fewer than 11 claims. Newly observed records do not establish new adoption. Claims include refills and are not unique patients.

## What this project demonstrates

Python API ingestion and validation; DuckDB SQL reporting layers; Tableau dashboard design; explicit business rules; reproducible CSV outputs; controlled-failure tests; and AI-assisted development with human review.

## Repository map

- `reports/`: short PDF write-up.
- `src/`, `sql/`, `tests/`: Python pipeline, SQL transformations, and tests.
- `config.json`: exact product definitions, geography, years, and pinned releases.
- `docs/`: metric dictionary, findings, Tableau reconciliation, and walkthrough.
- `evidence/`: validated year/state aggregates, cohort contributions, and rerun verification.

## Run locally

The original environment used Python 3.14.7. From the repository folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m src.check_environment
.venv/bin/python -m pytest -q
.venv/bin/python -m src.pipeline --config config.json
```

The first pipeline run downloads filtered public CMS records and may take time. After a successful download, rebuild with cached inputs:

```sh
.venv/bin/python -m src.pipeline --config config.json --offline
.venv/bin/python -m src.verify
```

Raw data, local environments, and generated database snapshots are not included. Tableau refresh and republishing are manual. The report and evidence files are saved snapshots; recheck them after rebuilding with different inputs or scope.

## Source and scope

[CMS Medicare Part D Prescribers by Provider and Drug](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug), 2023 and 2024 service years; 50 states and Washington, D.C.; 558,954 source records. Selected products: LYBALVI and exact generic-labeled Olanzapine, Aripiprazole, and Quetiapine Fumarate. Formulation is unresolved. See [metric definitions](docs/metric_dictionary.md).

## Quality and authorship

Two cached-input rebuilds produced identical export hashes. Duplicate, missing-column, and negative-claim inputs were rejected while valid outputs stayed unchanged. See [verification evidence](evidence/verification_summary.json).

Li Tian authored the Tableau dashboard and reviewed the workflow and reconciliations. Codex assisted with implementation, documentation, source inspection, and automated verification. This descriptive analysis does not establish clinical suitability, marketing causality, or sales ROI.
