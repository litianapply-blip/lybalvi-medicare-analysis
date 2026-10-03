# Tableau Dashboard and Refresh Guide

## Published dashboard

https://public.tableau.com/app/profile/li.tian7739/viz/LYBALVIMedicarePartDAnalysisWorkinProgress/LYBALVIPrescribingOverview

Scope: United States, 50 states and Washington, DC.
Source: CMS Medicare Part D, service years 2023–2024.

## Data sources

Keep these as separate sources; do not join them:
- state_summary.csv: one state and year per row.
- growth_components.csv: one observed-record cohort per year pair.

## Worksheet: 2024 claims by state

- Source: state_summary.csv
- Filter: Year = 2024
- Rows: State
- Columns: SUM(Lybalvi Claims)
- Sort: descending by claims
- Show claim labels.
- Tooltip: LYBALVI claims, selected-set claims,
  observed LYBALVI prescriber NPIs, and selected-set share.

Calculated share:
IF SUM([Selected Set Claims]) = 0 THEN NULL
ELSE SUM([Lybalvi Claims]) / SUM([Selected Set Claims])
END

Format share as a percentage with two decimal places.

## Worksheet: 2023 versus 2024

- Source: state_summary.csv
- Include both years.
- Rows: State, then discrete Year
- Columns: SUM(Lybalvi Claims)
- Color: discrete Year
- Include Year in the tooltip.

## Worksheet: nationwide growth contributions

- Source: growth_components.csv
- Rows: Cohort
- Columns: SUM(Observed Claim Change)
- Show labels.
- Include Observed Npis and the reporting-visibility caveat
  in the tooltip.
- Keep the comparison fixed to 2023–2024.

## Dashboard

- Top: 2024 state comparison
- Below: nationwide growth contributions
- Footer: source, scope, suppression and interpretation limits
- State filter: applies only to the state chart
- Default State selection: All
- Use Fit Width for the state chart; allow vertical scrolling.

## Verification

Use docs/tableau_reconciliation.md to check values.
Confirm the State filter does not change nationwide growth.
Publish and test the viewing link while signed out.

## Manual refresh

1. Rebuild and validate the local pipeline outputs.
2. Refresh or replace the corresponding uploaded Tableau sources.
3. Recheck values, calculations, and filter scope.
4. Update findings and reconciliation notes if results changed.
5. Republish and test the public viewing link.

CSV uploads do not automatically refresh from local files.
CMS observations are annual historical data, not a live feed.

## Troubleshooting learned during this build

A missing Hyper-item error occurred in an editing session.
Opening a fresh editor from the working published state view
allowed the growth worksheet and dashboard to be rebuilt.

If this recurs, preserve the existing editor, check the published
version, and avoid publishing from a failing session.