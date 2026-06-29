-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 04 — Gold business insights
-- MAGIC
-- MAGIC Produces the analyst-safe tables used by the Patient Signal Workbench:
-- MAGIC access KPIs, AI signal trends, a cohort comparison, and a concise
-- MAGIC business-impact record. No direct identifiers are present in Gold.

-- COMMAND ----------

USE CATALOG `patient_signal`;
USE SCHEMA `patient_signal`;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`gold_access_metrics`
COMMENT 'Monthly patient access KPIs by therapy, region, and payer.'
AS
SELECT
  CAST(DATE_TRUNC('MONTH', prescription_timestamp) AS DATE) AS prescription_month,
  therapy,
  region,
  payer_type,
  COUNT(*) AS patient_count,
  SUM(CASE WHEN treatment_outcome = 'started' THEN 1 ELSE 0 END) AS treatment_started_count,
  SUM(CASE WHEN treatment_outcome = 'abandoned' THEN 1 ELSE 0 END) AS treatment_abandoned_count,
  ROUND(AVG(CASE WHEN treatment_outcome = 'started' THEN 1.0 ELSE 0.0 END), 4) AS treatment_start_rate,
  APPROX_PERCENTILE(days_to_outcome, 0.5) AS median_days_to_outcome,
  CAST(SUM(estimated_annual_value_at_risk_usd) AS DECIMAL(18,2)) AS annual_value_at_risk_usd
FROM `patient_signal`.`patient_signal`.`silver_patient_journeys`
GROUP BY
  CAST(DATE_TRUNC('MONTH', prescription_timestamp) AS DATE),
  therapy,
  region,
  payer_type;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`gold_signal_metrics`
COMMENT 'Monthly aggregated de-identified AI signals for analyst filtering and trend analysis.'
AS
SELECT
  CAST(DATE_TRUNC('MONTH', feedback_timestamp) AS DATE) AS feedback_month,
  therapy,
  region,
  payer_type,
  barrier_category,
  sentiment,
  urgency,
  COUNT(*) AS signal_count,
  ROUND(AVG(barrier_confidence), 4) AS average_barrier_confidence,
  SUM(CASE WHEN review_required THEN 1 ELSE 0 END) AS review_required_count
FROM `patient_signal`.`patient_signal`.`silver_signal_extractions`
WHERE extraction_error IS NULL
GROUP BY
  CAST(DATE_TRUNC('MONTH', feedback_timestamp) AS DATE),
  therapy,
  region,
  payer_type,
  barrier_category,
  sentiment,
  urgency;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`gold_signal_detail`
COMMENT 'Feedback-level analyst evidence with masked text, AI labels, confidence, and review status.'
AS
SELECT
  feedback_id,
  feedback_timestamp,
  source,
  speaker_type,
  therapy,
  region,
  payer_type,
  barrier_category,
  barrier_confidence,
  sentiment,
  sentiment_confidence,
  urgency,
  urgency_confidence,
  signal_summary,
  evidence_excerpt,
  review_required
FROM `patient_signal`.`patient_signal`.`silver_signal_extractions`
WHERE extraction_error IS NULL;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`gold_cohort_comparison`
COMMENT 'Affected Therapy A Northeast Commercial cohort compared with all other synthetic journeys.'
AS
WITH labeled AS (
  SELECT
    CASE
      WHEN therapy = 'Therapy A'
        AND region = 'Northeast'
        AND payer_type = 'Commercial'
        AND CAST(prescription_timestamp AS DATE) >= DATE '2026-05-01'
      THEN 'Affected cohort'
      ELSE 'Comparison'
    END AS cohort,
    treatment_outcome,
    days_to_outcome,
    estimated_annual_value_at_risk_usd
  FROM `patient_signal`.`patient_signal`.`silver_patient_journeys`
)
SELECT
  cohort,
  COUNT(*) AS patient_count,
  SUM(CASE WHEN treatment_outcome = 'started' THEN 1 ELSE 0 END) AS treatment_started_count,
  SUM(CASE WHEN treatment_outcome = 'abandoned' THEN 1 ELSE 0 END) AS treatment_abandoned_count,
  ROUND(AVG(CASE WHEN treatment_outcome = 'started' THEN 1.0 ELSE 0.0 END), 4) AS treatment_start_rate,
  APPROX_PERCENTILE(days_to_outcome, 0.5) AS median_days_to_outcome,
  CAST(SUM(estimated_annual_value_at_risk_usd) AS DECIMAL(18,2)) AS annual_value_at_risk_usd
FROM labeled
GROUP BY cohort;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`gold_business_impact`
COMMENT 'Executive estimate of incremental patient starts and annual value at risk in the affected cohort.'
AS
WITH rates AS (
  SELECT
    MAX(CASE WHEN cohort = 'Affected cohort' THEN patient_count END) AS affected_patient_count,
    MAX(CASE WHEN cohort = 'Affected cohort' THEN treatment_started_count END) AS affected_started_count,
    MAX(CASE WHEN cohort = 'Affected cohort' THEN treatment_start_rate END) AS affected_start_rate,
    MAX(CASE WHEN cohort = 'Affected cohort' THEN median_days_to_outcome END) AS affected_median_days,
    MAX(CASE WHEN cohort = 'Comparison' THEN treatment_start_rate END) AS comparison_start_rate,
    MAX(CASE WHEN cohort = 'Comparison' THEN median_days_to_outcome END) AS comparison_median_days
  FROM `patient_signal`.`patient_signal`.`gold_cohort_comparison`
), calculated AS (
  SELECT
    *,
    GREATEST(0, ROUND(affected_patient_count * comparison_start_rate) - affected_started_count) AS estimated_excess_starts_at_risk
  FROM rates
)
SELECT
  'Therapy A — Northeast Commercial access deterioration' AS business_signal,
  affected_patient_count,
  affected_start_rate,
  comparison_start_rate,
  ROUND((comparison_start_rate - affected_start_rate) * 100, 1) AS start_rate_gap_percentage_points,
  affected_median_days,
  comparison_median_days,
  estimated_excess_starts_at_risk,
  CAST(
    estimated_excess_starts_at_risk *
    (SELECT annual_net_value_per_start_usd
     FROM `patient_signal`.`patient_signal`.`bronze_therapy_reference`
     WHERE therapy = 'Therapy A')
    AS DECIMAL(18,2)
  ) AS estimated_incremental_annual_value_at_risk_usd,
  'Investigate prior-authorization and specialty-pharmacy workflows with Northeast commercial payers.' AS recommended_action
FROM calculated;

-- COMMAND ----------
-- MAGIC %md
-- MAGIC ## Demo outputs

-- COMMAND ----------

SELECT *
FROM `patient_signal`.`patient_signal`.`gold_business_impact`;

SELECT *
FROM `patient_signal`.`patient_signal`.`gold_cohort_comparison`
ORDER BY cohort;

SELECT
  barrier_category,
  SUM(signal_count) AS signal_count,
  ROUND(AVG(average_barrier_confidence), 3) AS average_confidence
FROM `patient_signal`.`patient_signal`.`gold_signal_metrics`
WHERE therapy = 'Therapy A'
  AND region = 'Northeast'
  AND payer_type = 'Commercial'
  AND feedback_month >= DATE '2026-05-01'
GROUP BY barrier_category
ORDER BY signal_count DESC;

-- COMMAND ----------
-- MAGIC %md
-- MAGIC ## Production permission pattern
-- MAGIC
-- MAGIC Keep Bronze restricted. Grant the analyst group access only to approved
-- MAGIC Silver/Gold tables after replacing `medpulse_analysts` with a real group.

-- COMMAND ----------

-- GRANT USE CATALOG ON CATALOG `patient_signal` TO `medpulse_analysts`;
-- GRANT USE SCHEMA ON SCHEMA `patient_signal`.`patient_signal` TO `medpulse_analysts`;
-- GRANT SELECT ON TABLE `patient_signal`.`patient_signal`.`gold_access_metrics` TO `medpulse_analysts`;
-- GRANT SELECT ON TABLE `patient_signal`.`patient_signal`.`gold_signal_metrics` TO `medpulse_analysts`;
-- GRANT SELECT ON TABLE `patient_signal`.`patient_signal`.`gold_signal_detail` TO `medpulse_analysts`;
-- GRANT SELECT ON TABLE `patient_signal`.`patient_signal`.`gold_business_impact` TO `medpulse_analysts`;

