-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 01 — Bronze ingestion
-- MAGIC
-- MAGIC Loads the uploaded synthetic source files into managed Delta tables.
-- MAGIC Bronze preserves direct identifiers and raw text, so access to these
-- MAGIC tables should remain restricted to the data engineering role.

-- COMMAND ----------

USE CATALOG `patient_signal`;
USE SCHEMA `patient_signal`;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`bronze_patients_raw`
COMMENT 'Restricted synthetic patient profiles exactly as landed, plus ingestion metadata.'
AS
SELECT
  patient_id,
  member_id,
  full_name,
  date_of_birth,
  postal_code,
  phone_number,
  region,
  payer_type,
  therapy,
  diagnosis_date,
  analytics_consent,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/patient_signal/patient_signal/patient_signal_files/raw/patients_raw.csv',
  format => 'csv',
  header => true,
  mode => 'FAILFAST',
  schema => 'patient_id STRING, member_id STRING, full_name STRING, date_of_birth DATE, postal_code STRING, phone_number STRING, region STRING, payer_type STRING, therapy STRING, diagnosis_date DATE, analytics_consent BOOLEAN'
);

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`bronze_journey_events_raw`
COMMENT 'Synthetic patient access journey events at one row per event.'
AS
SELECT
  event_id,
  patient_id,
  event_timestamp,
  stage_order,
  journey_stage,
  event_outcome,
  delay_days,
  NULLIF(TRIM(barrier_category), '') AS barrier_category,
  source_system,
  therapy,
  region,
  payer_type,
  estimated_annual_value_at_risk_usd,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/patient_signal/patient_signal/patient_signal_files/raw/journey_events_raw.csv',
  format => 'csv',
  header => true,
  mode => 'FAILFAST',
  schema => 'event_id STRING, patient_id STRING, event_timestamp TIMESTAMP, stage_order INT, journey_stage STRING, event_outcome STRING, delay_days INT, barrier_category STRING, source_system STRING, therapy STRING, region STRING, payer_type STRING, estimated_annual_value_at_risk_usd DECIMAL(18,2)'
);

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`bronze_feedback_raw`
COMMENT 'Restricted raw call-center and survey feedback. Some rows deliberately contain synthetic identifiers.'
AS
SELECT
  feedback_id,
  patient_id,
  feedback_timestamp,
  source,
  speaker_type,
  therapy,
  region,
  payer_type,
  feedback_text,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/patient_signal/patient_signal/patient_signal_files/raw/feedback_raw.jsonl',
  format => 'json',
  mode => 'FAILFAST',
  schema => 'feedback_id STRING, patient_id STRING, feedback_timestamp TIMESTAMP, source STRING, speaker_type STRING, therapy STRING, region STRING, payer_type STRING, feedback_text STRING'
);

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`bronze_analyst_annotations_raw`
COMMENT 'Historical manual annotations used for review and model-quality comparison.'
AS
SELECT
  annotation_id,
  feedback_id,
  analyst_alias,
  annotated_barrier_category,
  annotated_sentiment,
  annotation_status,
  annotation_note,
  annotated_at,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/patient_signal/patient_signal/patient_signal_files/raw/analyst_annotations_raw.csv',
  format => 'csv',
  header => true,
  mode => 'FAILFAST',
  schema => 'annotation_id STRING, feedback_id STRING, analyst_alias STRING, annotated_barrier_category STRING, annotated_sentiment STRING, annotation_status STRING, annotation_note STRING, annotated_at TIMESTAMP'
);

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`bronze_therapy_reference`
COMMENT 'Fictional therapy reference data and commercial-value assumptions.'
AS
SELECT
  therapy,
  therapeutic_area,
  annual_net_value_per_start_usd,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/patient_signal/patient_signal/patient_signal_files/raw/therapy_reference.csv',
  format => 'csv',
  header => true,
  mode => 'FAILFAST',
  schema => 'therapy STRING, therapeutic_area STRING, annual_net_value_per_start_usd DECIMAL(18,2)'
);

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`validation_signal_ground_truth`
COMMENT 'Restricted holdout labels for evaluating AI extraction. Never exposed to the analyst application.'
AS
SELECT
  feedback_id,
  expected_barrier_category,
  expected_sentiment,
  expected_urgency,
  expected_journey_stage,
  contains_sensitive_data,
  expected_review_required,
  _metadata.file_path AS source_file,
  current_timestamp() AS ingested_at
FROM read_files(
  '/Volumes/patient_signal/patient_signal/patient_signal_files/validation/signal_ground_truth.csv',
  format => 'csv',
  header => true,
  mode => 'FAILFAST',
  schema => 'feedback_id STRING, expected_barrier_category STRING, expected_sentiment STRING, expected_urgency STRING, expected_journey_stage STRING, contains_sensitive_data BOOLEAN, expected_review_required BOOLEAN'
);

-- COMMAND ----------
-- MAGIC %md
-- MAGIC ## Ingestion checks
-- MAGIC Every row count should return `PASS`.

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`bronze_ingestion_audit`
COMMENT 'Latest POC ingestion row-count checks.'
AS
SELECT 'bronze_patients_raw' AS table_name, COUNT(*) AS actual_rows, 5000 AS expected_rows, current_timestamp() AS checked_at
FROM `patient_signal`.`patient_signal`.`bronze_patients_raw`
UNION ALL
SELECT 'bronze_journey_events_raw', COUNT(*), 30000, current_timestamp()
FROM `patient_signal`.`patient_signal`.`bronze_journey_events_raw`
UNION ALL
SELECT 'bronze_feedback_raw', COUNT(*), 4000, current_timestamp()
FROM `patient_signal`.`patient_signal`.`bronze_feedback_raw`
UNION ALL
SELECT 'bronze_analyst_annotations_raw', COUNT(*), 200, current_timestamp()
FROM `patient_signal`.`patient_signal`.`bronze_analyst_annotations_raw`
UNION ALL
SELECT 'validation_signal_ground_truth', COUNT(*), 500, current_timestamp()
FROM `patient_signal`.`patient_signal`.`validation_signal_ground_truth`;

SELECT
  table_name,
  actual_rows,
  expected_rows,
  CASE WHEN actual_rows = expected_rows THEN 'PASS' ELSE 'FAIL' END AS status
FROM `patient_signal`.`patient_signal`.`bronze_ingestion_audit`
ORDER BY table_name;

