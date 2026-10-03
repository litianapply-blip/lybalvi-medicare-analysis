-- Only executed when both 2023 and 2024 have validated coverage.
-- COALESCE supplies contributions to observed released volume; it does not
-- establish zero prescribing for an NPI whose record was not published.
CREATE TABLE growth_detail AS
WITH before AS (
    SELECT * FROM prescriber_product_year WHERE is_focal AND year = 2023
), after AS (
    SELECT * FROM prescriber_product_year WHERE is_focal AND year = 2024
)
SELECT COALESCE(b.npi, a.npi) AS npi,
       CASE WHEN b.npi IS NOT NULL AND a.npi IS NOT NULL THEN 'Continuing observed records'
            WHEN b.npi IS NULL THEN 'Newly observed records'
            ELSE 'No-longer-observed records' END AS cohort,
       b.claims AS claims_2023, a.claims AS claims_2024,
       COALESCE(a.claims, 0) - COALESCE(b.claims, 0) AS observed_claim_change,
       b.city AS city_2023, a.city AS city_2024,
       b.specialty AS specialty_2023, a.specialty AS specialty_2024,
       CASE WHEN b.npi IS NOT NULL AND a.npi IS NOT NULL
            THEN (b.city <> a.city OR b.state <> a.state) ELSE NULL END AS city_changed,
       CASE WHEN b.npi IS NOT NULL AND a.npi IS NOT NULL
            THEN b.specialty <> a.specialty ELSE NULL END AS specialty_changed
FROM before b FULL OUTER JOIN after a ON b.npi = a.npi;

CREATE TABLE growth_components AS
SELECT 2023 AS baseline_year, 2024 AS comparison_year, cohort,
       COUNT(*)::BIGINT AS observed_npis,
       SUM(COALESCE(claims_2023, 0))::BIGINT AS observed_claims_2023,
       SUM(COALESCE(claims_2024, 0))::BIGINT AS observed_claims_2024,
       SUM(observed_claim_change)::BIGINT AS observed_claim_change
FROM growth_detail GROUP BY cohort;

CREATE TABLE year_growth AS
SELECT 2023 AS baseline_year, 2024 AS comparison_year,
       b.lybalvi_claims AS lybalvi_claims_2023,
       a.lybalvi_claims AS lybalvi_claims_2024,
       a.lybalvi_claims - b.lybalvi_claims AS observed_claim_change,
       (a.lybalvi_claims - b.lybalvi_claims) / NULLIF(b.lybalvi_claims, 0) AS observed_yoy_change
FROM year_summary b CROSS JOIN year_summary a WHERE b.year = 2023 AND a.year = 2024;

CREATE TABLE provider_attribute_changes AS
SELECT COUNT(*)::BIGINT AS continuing_selected_set_npis,
       COUNT(*) FILTER (WHERE (b.city <> a.city OR b.state <> a.state))::BIGINT AS city_changed_npis,
       COUNT(*) FILTER (WHERE b.specialty <> a.specialty)::BIGINT AS specialty_changed_npis
FROM prescriber_year b JOIN prescriber_year a USING (npi)
WHERE b.year = 2023 AND a.year = 2024;
