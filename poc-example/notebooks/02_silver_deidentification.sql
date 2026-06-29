-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 02 — Silver de-identification and journey curation
-- MAGIC
-- MAGIC Removes direct identifiers, replaces the raw patient ID with a stable
-- MAGIC surrogate key, masks synthetic identifiers in feedback text, and creates
-- MAGIC one curated patient-journey record per patient.

-- COMMAND ----------

USE CATALOG `patient_signal`;
USE SCHEMA `patient_signal`;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_patients_deidentified`
COMMENT 'Analyst-safe patient cohort attributes with no direct patient identifiers.'
AS
WITH aged AS (
  SELECT
    SHA2(CONCAT('patient-signal-poc:', patient_id), 256) AS patient_key,
    FLOOR(MONTHS_BETWEEN(DATE '2026-06-27', date_of_birth) / 12) AS age_years,
    region,
    payer_type,
    therapy,
    CAST(DATE_TRUNC('MONTH', diagnosis_date) AS DATE) AS diagnosis_month,
    analytics_consent,
    ingested_at
  FROM `patient_signal`.`patient_signal`.`bronze_patients_raw`
)
SELECT
  patient_key,
  CASE
    WHEN age_years BETWEEN 18 AND 34 THEN '18-34'
    WHEN age_years BETWEEN 35 AND 49 THEN '35-49'
    WHEN age_years BETWEEN 50 AND 64 THEN '50-64'
    WHEN age_years >= 65 THEN '65+'
    ELSE 'Unknown'
  END AS age_band,
  region,
  payer_type,
  therapy,
  diagnosis_month,
  analytics_consent,
  ingested_at
FROM aged;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_journey_events`
COMMENT 'De-identified access journey events linked by surrogate patient key.'
AS
SELECT
  event_id,
  SHA2(CONCAT('patient-signal-poc:', patient_id), 256) AS patient_key,
  event_timestamp,
  CAST(event_timestamp AS DATE) AS event_date,
  stage_order,
  journey_stage,
  event_outcome,
  delay_days,
  barrier_category,
  source_system,
  therapy,
  region,
  payer_type,
  CAST(estimated_annual_value_at_risk_usd AS DECIMAL(18,2)) AS estimated_annual_value_at_risk_usd,
  ingested_at
FROM `patient_signal`.`patient_signal`.`bronze_journey_events_raw`;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_feedback_deidentified`
COMMENT 'Feedback text with direct identifiers removed before AI processing or analyst access.'
AS
WITH detected AS (
  SELECT
    feedback_id,
    SHA2(CONCAT('patient-signal-poc:', patient_id), 256) AS patient_key,
    feedback_timestamp,
    source,
    speaker_type,
    therapy,
    region,
    payer_type,
    feedback_text,
    feedback_text RLIKE 'member MP-[0-9]{8}|DOB [0-9]{4}-[0-9]{2}-[0-9]{2}' AS sensitive_data_detected,
    ingested_at
  FROM `patient_signal`.`patient_signal`.`bronze_feedback_raw`
)
SELECT
  feedback_id,
  patient_key,
  feedback_timestamp,
  source,
  speaker_type,
  therapy,
  region,
  payer_type,
  REGEXP_REPLACE(
    REGEXP_REPLACE(
      feedback_text,
      'Patient [^,]+, member MP-[0-9]{8}, DOB [0-9]{4}-[0-9]{2}-[0-9]{2}:',
      'Patient [MASKED], member [MASKED], DOB [MASKED]:'
    ),
    'MP-[0-9]{8}',
    '[MASKED]'
  ) AS feedback_text_safe,
  sensitive_data_detected,
  ingested_at
FROM detected;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_analyst_annotations`
COMMENT 'Manual review labels linked only to de-identified feedback records.'
AS
SELECT
  a.annotation_id,
  a.feedback_id,
  a.analyst_alias,
  a.annotated_barrier_category,
  a.annotated_sentiment,
  a.annotation_status,
  a.annotation_note,
  a.annotated_at
FROM `patient_signal`.`patient_signal`.`bronze_analyst_annotations_raw` AS a
INNER JOIN `patient_signal`.`patient_signal`.`silver_feedback_deidentified` AS f
  ON a.feedback_id = f.feedback_id;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_patient_journeys`
COMMENT 'One de-identified accumulating journey record per patient.'
AS
SELECT
  patient_key,
  MAX(therapy) AS therapy,
  MAX(region) AS region,
  MAX(payer_type) AS payer_type,
  MIN(CASE WHEN journey_stage = 'prescription_written' THEN event_timestamp END) AS prescription_timestamp,
  MAX(CASE WHEN journey_stage = 'treatment_outcome' THEN event_timestamp END) AS outcome_timestamp,
  MAX(CASE WHEN journey_stage = 'treatment_outcome' THEN event_outcome END) AS treatment_outcome,
  MAX(CASE WHEN journey_stage = 'treatment_outcome' THEN delay_days END) AS days_to_outcome,
  MAX(CASE WHEN journey_stage = 'treatment_outcome' THEN barrier_category END) AS final_barrier_category,
  MAX(CASE WHEN journey_stage = 'treatment_outcome' THEN estimated_annual_value_at_risk_usd END) AS estimated_annual_value_at_risk_usd
FROM `patient_signal`.`patient_signal`.`silver_journey_events`
GROUP BY patient_key;

-- COMMAND ----------
-- MAGIC %md
-- MAGIC ## Governance and quality checks
-- MAGIC The final check must return zero. Direct identifiers remain only in Bronze.

-- COMMAND ----------

SELECT
  (SELECT COUNT(*) FROM `patient_signal`.`patient_signal`.`silver_patients_deidentified`) AS patient_rows,
  (SELECT COUNT(*) FROM `patient_signal`.`patient_signal`.`silver_journey_events`) AS journey_event_rows,
  (SELECT COUNT(*) FROM `patient_signal`.`patient_signal`.`silver_feedback_deidentified`) AS feedback_rows,
  (SELECT COUNT(*) FROM `patient_signal`.`patient_signal`.`silver_patient_journeys`) AS patient_journey_rows,
  (
    SELECT COUNT(*)
    FROM `patient_signal`.`patient_signal`.`silver_feedback_deidentified`
    WHERE feedback_text_safe RLIKE 'MP-[0-9]{8}|DOB [0-9]{4}-[0-9]{2}-[0-9]{2}'
  ) AS unmasked_sensitive_text_rows;

