# Tableau Reconciliation — Nationwide Dashboard

Scope: 50 states and Washington, DC; CMS Medicare Part D,
service years 2023–2024.

## Nationwide totals

2023:
- Observed LYBALVI claims: 39,134
- Selected-set claims: 14,295,635
- Observed LYBALVI prescriber NPIs: 1,623
- Selected-set share: approximately 0.274%

2024:
- Observed LYBALVI claims: 57,090
- Selected-set claims: 14,933,828
- Observed LYBALVI prescriber NPIs: 2,344
- Selected-set share: approximately 0.382%

## State-chart checks

With Year = 2024:
- California: 5,299 observed LYBALVI claims
- California: 219 observed LYBALVI prescriber NPIs
- California selected-set share: 0.41% when rounded to two decimals
- Massachusetts: 777 observed LYBALVI claims

California's 2023 observed LYBALVI claims: 3,589.

## Nationwide growth-contribution checks

- Continuing observed records: +5,906 claims
- Newly observed records: +19,727 claims
- No-longer-observed records: -7,677 claims
- Net increase: 17,956 claims, or approximately 45.9%

## Filter checks

The State filter affects only the state chart.
Selecting MA should show 777 claims for 2024.
The nationwide growth contributions must remain unchanged.
Reset State to All before publishing the default view.

## Calculation checks

Share = SUM(LYBALVI claims) / SUM(selected-set claims).
Do not average row-level percentages.
Do not sum distinct prescriber counts across products or years.

## Interpretation

Claims include refills, not unique patients.
Missing published records do not establish zero prescribing.
The comparison set contains four explicitly selected products,
not the full market. Formulation is not resolved.

Recheck this document if source data, scope, or calculations change.