# Metric dictionary

## Scope and comparison set

United States prescriber locations: 50 states and Washington, DC. Medicare Part D service years 2023 and 2024. The denominator contains only these exact CMS brand/generic pairs:

| Output product | CMS Brnd_Name | CMS Gnrc_Name |
|---|---|---|
| LYBALVI | Lybalvi | Olanzapine/Samidorphan Malate |
| Generic olanzapine | Olanzapine | Olanzapine |
| Generic aripiprazole | Aripiprazole | Aripiprazole |
| Generic quetiapine fumarate | Quetiapine Fumarate | Quetiapine Fumarate |

This is a pragmatic four-product benchmark, not a full antipsychotic market or a clinically interchangeable treatment set. Other brands, combination products and explicitly named injectable products are outside this exact-name selection. The source has no dosage-form, NDC or route field: some selected generic/brand labels may aggregate formulations. Do not describe the set as oral-only. Olanzapine injection exists under the olanzapine name: [DailyMed label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=12ce860a-6f22-4db6-8acf-786b40f5a5a5).

## Source mapping

| Output | Source | Treatment |
|---|---|---|
| year | Pinned release temporal coverage | Integer service year, not publication year |
| npi | Prscrbr_NPI | Ten-character string |
| state | Prscrbr_State_Abrvtn | Actual prescriber state; 50 states plus DC.|
| city | Prscrbr_City | Trimmed uppercase; original retained as source_city |
| specialty | Prscrbr_Type | Trimmed; original retained as source_specialty |
| source_brand / source_generic | Brnd_Name / Gnrc_Name | Preserved exactly; explicit pair-to-product mapping |
| claims | Tot_Clms | Integer prescription claims, including refills; required |
| standardized_30day_fills | Tot_30day_Fills | Separate numeric supply-standardized measure; missing retained |
| days_supply | Tot_Day_Suply | Nullable integer |
| drug_cost | Tot_Drug_Cst | Nullable amount; DECIMAL(18,2) in DuckDB |
| beneficiaries | Tot_Benes | Nullable integer for inspection only; never aggregated across records |

The original 22-field JSON responses remain unchanged in data/raw. Provider names and age-specific fields remain there but are not included in dashboard exports. A year/NPI/brand/generic combination must be unique. All four configured pairs must be observed in every configured year; unexpected absence stops the pipeline for review.

## Reporting grains

| Table | One row represents | Intended use |
|---|---|---|
| state_summary | State + year | Used for state comparisons
| prescriber_product_year | NPI + product + year | Local fact table and downloadable selected data |
| prescriber_year | NPI + year | Local prescriber accounting; absent LYBALVI record remains NULL |
| product_year | Product + year | Product comparison |
| year_summary | Year | Use year_summary for nationwide totals and distinct counts. Use state_summary for state-level totals and distinct counts. |
| segment_year | State + segment type + segment + year | Separate city and specialty views |
| investigation_segments | State + segment type + segment + year + threshold | Screening with explicit threshold sensitivity |
| growth_detail | NPI observed for LYBALVI in either year | Local accounting; no public individual-provider view |
| growth_components | Observed record cohort + year pair | Contributions to observed change |
| year_growth | Year pair | Overall observed change and percentage |
| provider_attribute_changes | Year pair (2023/2024) | Count of provider location/specialty changes within the observed selected-set cohort |

## Metric definitions

- **lybalvi_claims:** sum of Tot_Clms in published LYBALVI records. Dashboard labels should say "Observed LYBALVI claims (including refills)". This is not unique patients, new starts or standardized 30-day fills.
- **selected_set_claims:** sum of Tot_Clms over all four exact pairs above, including LYBALVI.
- **observed_selected_set_share:** lybalvi_claims / selected_set_claims. Zero denominators yield NULL. In Tableau, use the ratio of summed claims, never the average of row percentages. Do not filter the denominator down to only LYBALVI.
- **lybalvi_observed_prescribers:** distinct NPI with a published positive LYBALVI record. Includes any organizational NPIs that CMS reports; not necessarily unique individual clinicians.
- **selected_set_observed_prescribers:** distinct NPI across the four selected products. Do not sum product-specific distinct counts.
- **observed_yoy_change:** (2024 observed LYBALVI claims - 2023 observed LYBALVI claims) / 2023 observed LYBALVI claims. Missing or zero baseline gives NULL.
- **Continuing observed records:** NPI has a published LYBALVI record in both years; contribution is 2024 minus 2023 claims.
- **Newly observed records:** NPI has a published LYBALVI record in 2024 only; contribution is its 2024 claims. Does not establish true adoption or a new prescriber.
- **No-longer-observed records:** NPI has a published LYBALVI record in 2023 only; contribution is negative 2023 claims. Does not establish cessation or exit.

For cohort contribution arithmetic only, an unavailable released record contributes zero to the observed total. Individual missing records are retained as NULL in the underlying models. Cohort components must sum exactly to the total change.

## Screening rule

Use segments with at least 1,000 selected-set claims and observed LYBALVI share below that year’s selected-set share for the segment’s own state. Rank eligible segments within each state, year, segment type, and threshold by selected-set claims, largest first; show volume and share separately. This analyst-chosen threshold is not a clinical or commercial standard. Exports also show thresholds of 500 and 2,000. Filter to exactly one threshold before using investigation_segments. Call these "segments for investigation," not sales potential or ROI predictions.
Compare each city or specialty segment with its own state's
selected-set share for the same year. Rank eligible segments
separately within each state, year, segment type, and threshold.

## Interpretation and filter limits

- CMS excludes provider-drug records with fewer than 11 claims. Blank beneficiary counts represent suppression, not zero. Summed detail totals understate full Part D volume.
- Data describe Medicare Part D, not all payers. Claims do not reveal diagnosis, treatment suitability, marketing effects or manufacturer revenue. Drug cost is paid claim cost and does not reflect manufacturer rebates.
- City is provider location, not patient residence or an actual sales territory. No ZIP field was returned in this provider/drug dataset. Provider demographics can reflect a later NPPES snapshot than the service year.
- City and specialty rows summarize the same underlying records. Select exactly one segment type before summing claims. summing both doubles claims.
- Counts are not additive across products, years or the two segment types. Use year_summary for statewide distinct counts. Within one year and one segment type, provider attributes were checked for consistency.
- Changing locations or specialties can move segment totals. Consult provider_attribute_changes and growth_detail; do not interpret every segment change as prescribing growth among an unchanged cohort.
- Product totals must not be joined to prescriber rows or segment totals in Tableau. Start with separate data sources and sheets.
- year_summary contains nationwide distinct counts and state_summary for state-level distinct counts. sCity labels include the state to distinguish places
with the same name. The dashboard's State filter affects only
the state chart. Growth contributions remain nationwide.
## Official sources

- [CMS dataset and release selector](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug)
- [CMS dictionary](https://data.cms.gov/resources/medicare-part-d-prescribers-by-provider-and-drug-data-dictionary)
- [CMS methodology, April 2026](https://data.cms.gov/sites/default/files/2026-05/MUP_DPR_RY26_20260421_Methodology_508.pdf)
- [CMS API documentation](https://data.cms.gov/api-docs)

Exact release URLs, retrieval times, page sizes, schemas and SHA-256 checksums are recorded in outputs/run_manifest.json.
