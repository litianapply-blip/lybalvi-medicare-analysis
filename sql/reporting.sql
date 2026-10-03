-- Input is one validated year/NPI/product record. Tot_Clms includes refills.
CREATE TABLE prescriber_product_year AS
SELECT year, npi, state, city, specialty, source_city, source_specialty,
       source_brand, source_generic, product, is_focal, claims,
       standardized_30day_fills, days_supply,
       CAST(drug_cost AS DECIMAL(18,2)) AS drug_cost, beneficiaries
FROM clean_input;

-- Keep an absent focal record NULL at the individual NPI level.
CREATE TABLE prescriber_year AS
SELECT year, npi, state, city, specialty,
       SUM(claims)::BIGINT AS selected_set_claims,
       SUM(claims) FILTER (WHERE is_focal)::BIGINT AS lybalvi_claims,
       COUNT(*) FILTER (WHERE is_focal) > 0 AS lybalvi_record_observed,
       SUM(claims) FILTER (WHERE is_focal) / NULLIF(SUM(claims), 0) AS observed_selected_set_share
FROM prescriber_product_year
GROUP BY year, npi, state, city, specialty;

CREATE TABLE product_year AS
SELECT year, product, is_focal, SUM(claims)::BIGINT AS claims,
       COUNT(DISTINCT npi)::BIGINT AS observed_prescribers,
       CASE WHEN COUNT(standardized_30day_fills) = COUNT(*)
            THEN SUM(CAST(standardized_30day_fills AS DECIMAL(24,10))) END AS standardized_30day_fills,
       CASE WHEN COUNT(drug_cost) = COUNT(*) THEN SUM(drug_cost) END AS drug_cost
FROM prescriber_product_year
GROUP BY year, product, is_focal;

-- Aggregate zeros count released focal-record contributions, not confirmed inactivity.
CREATE TABLE year_summary AS
SELECT year,
       SUM(claims)::BIGINT AS selected_set_claims,
       SUM(CASE WHEN is_focal THEN claims ELSE 0 END)::BIGINT AS lybalvi_claims,
       COUNT(DISTINCT npi)::BIGINT AS selected_set_observed_prescribers,
       COUNT(DISTINCT npi) FILTER (WHERE is_focal)::BIGINT AS lybalvi_observed_prescribers,
       SUM(CASE WHEN is_focal THEN claims ELSE 0 END) / NULLIF(SUM(claims), 0) AS observed_selected_set_share
FROM prescriber_product_year GROUP BY year;

CREATE TABLE state_summary AS
SELECT year, state,
       SUM(claims)::BIGINT AS selected_set_claims,
       SUM(CASE WHEN is_focal THEN claims ELSE 0 END)::BIGINT AS lybalvi_claims,
       COUNT(DISTINCT npi)::BIGINT AS selected_set_observed_prescribers,
       COUNT(DISTINCT npi) FILTER (WHERE is_focal)::BIGINT AS lybalvi_observed_prescribers,
       SUM(CASE WHEN is_focal THEN claims ELSE 0 END) / NULLIF(SUM(claims), 0) AS observed_selected_set_share
FROM prescriber_product_year GROUP BY year, state;

CREATE TABLE segment_year AS
WITH segments AS (
    SELECT *, 'City' AS segment_type, city || ', ' || state AS segment FROM prescriber_product_year
    UNION ALL
    SELECT *, 'Specialty' AS segment_type, specialty AS segment FROM prescriber_product_year
)
SELECT year, state, segment_type, segment,
       SUM(claims)::BIGINT AS selected_set_claims,
       SUM(CASE WHEN is_focal THEN claims ELSE 0 END)::BIGINT AS lybalvi_claims,
       COUNT(DISTINCT npi)::BIGINT AS selected_set_observed_prescribers,
       COUNT(DISTINCT npi) FILTER (WHERE is_focal)::BIGINT AS lybalvi_observed_prescribers,
       SUM(CASE WHEN is_focal THEN claims ELSE 0 END) / NULLIF(SUM(claims), 0) AS observed_selected_set_share
FROM segments GROUP BY year, state, segment_type, segment;

-- Thresholds are explicit analyst choices, not estimates of sales potential.
CREATE TABLE investigation_segments AS
SELECT s.*, t.claim_threshold,
       y.observed_selected_set_share AS statewide_observed_share,
       s.observed_selected_set_share < y.observed_selected_set_share AS below_statewide_share,
       DENSE_RANK() OVER (PARTITION BY s.year, s.state, s.segment_type, t.claim_threshold
                         ORDER BY s.selected_set_claims DESC, s.segment) AS volume_rank
FROM segment_year s
JOIN state_summary y USING (year, state)
CROSS JOIN thresholds t
WHERE s.selected_set_claims >= t.claim_threshold
  AND s.observed_selected_set_share < y.observed_selected_set_share;
