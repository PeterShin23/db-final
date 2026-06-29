-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 03 — AI signal extraction
-- MAGIC
-- MAGIC Uses one task-specific `ai_extract` 2.1 call per feedback record to
-- MAGIC identify the access barrier, sentiment, urgency, and concise summary.
-- MAGIC Confidence scores and source citations make uncertain results reviewable.
-- MAGIC
-- MAGIC The POC processes a deterministic 1,000-row sample to control runtime and
-- MAGIC token consumption. Change `sample_rank <= 1000` to `<= 4000` for the full
-- MAGIC synthetic dataset.

-- COMMAND ----------

USE CATALOG `patient_signal`;
USE SCHEMA `patient_signal`;

-- COMMAND ----------
-- MAGIC %md
-- MAGIC ## Preflight
-- MAGIC This requires a serverless SQL warehouse or supported notebook compute.

-- COMMAND ----------

SELECT ai_extract(
  'Coverage for Therapy A was denied and an urgent appeal is required.',
  '{
    "barrier_category": {
      "type": "enum",
      "labels": ["prior_authorization", "specialty_pharmacy_delay", "payer_denial", "out_of_pocket_cost", "step_therapy", "scheduling", "patient_concern", "no_barrier"],
      "description": "Primary treatment access barrier"
    },
    "sentiment": {
      "type": "enum",
      "labels": ["positive", "negative", "neutral", "mixed"]
    },
    "urgency": {
      "type": "enum",
      "labels": ["high", "medium", "low"]
    },
    "summary": {
      "type": "string",
      "description": "Concise factual summary no longer than 25 words"
    }
  }',
  options => map(
    'version', '2.1',
    'enableConfidenceScores', 'true',
    'enableCitations', 'true',
    'instructions', 'Extract one governed patient access signal. Do not infer facts absent from the text.'
  )
) AS preflight_result;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_signal_ai_raw`
COMMENT 'Raw structured output from ai_extract 2.1. Restricted for debugging and evaluation.'
AS
WITH ranked_feedback AS (
  SELECT
    feedback_id,
    feedback_timestamp,
    source,
    speaker_type,
    therapy,
    region,
    payer_type,
    feedback_text_safe,
    sensitive_data_detected,
    ROW_NUMBER() OVER (ORDER BY XXHASH64(feedback_id)) AS sample_rank
  FROM `patient_signal`.`patient_signal`.`silver_feedback_deidentified`
)
SELECT
  feedback_id,
  feedback_timestamp,
  source,
  speaker_type,
  therapy,
  region,
  payer_type,
  feedback_text_safe,
  sensitive_data_detected,
  ai_extract(
    feedback_text_safe,
    '{
      "barrier_category": {
        "type": "enum",
        "labels": ["prior_authorization", "specialty_pharmacy_delay", "payer_denial", "out_of_pocket_cost", "step_therapy", "scheduling", "patient_concern", "no_barrier"],
        "description": "The single primary barrier preventing or delaying treatment access"
      },
      "sentiment": {
        "type": "enum",
        "labels": ["positive", "negative", "neutral", "mixed"],
        "description": "Sentiment expressed in the feedback"
      },
      "urgency": {
        "type": "enum",
        "labels": ["high", "medium", "low"],
        "description": "Urgency based only on treatment delay or access risk stated in the text"
      },
      "summary": {
        "type": "string",
        "description": "A factual summary of the access signal in 25 words or fewer"
      }
    }',
    options => map(
      'version', '2.1',
      'enableConfidenceScores', 'true',
      'enableCitations', 'true',
      'instructions', 'These are de-identified life-sciences access feedback records. Extract only information supported by the text. Select exactly one primary barrier.'
    )
  ) AS ai_result,
  current_timestamp() AS ai_processed_at
FROM ranked_feedback
WHERE sample_rank <= 1000;

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`silver_signal_extractions`
COMMENT 'Parsed, reviewable AI signals with confidence, evidence, and error fields.'
AS
WITH parsed AS (
  SELECT
    feedback_id,
    feedback_timestamp,
    source,
    speaker_type,
    therapy,
    region,
    payer_type,
    feedback_text_safe,
    sensitive_data_detected,
    ai_result:response.barrier_category.value::STRING AS barrier_category,
    ai_result:response.barrier_category.confidence_score::DOUBLE AS barrier_confidence,
    ai_result:response.sentiment.value::STRING AS sentiment,
    ai_result:response.sentiment.confidence_score::DOUBLE AS sentiment_confidence,
    ai_result:response.urgency.value::STRING AS urgency,
    ai_result:response.urgency.confidence_score::DOUBLE AS urgency_confidence,
    ai_result:response.summary.value::STRING AS signal_summary,
    ai_result:response.summary.confidence_score::DOUBLE AS summary_confidence,
    ai_result:metadata AS citation_metadata,
    ai_result:error_message::STRING AS extraction_error,
    ai_processed_at
  FROM `patient_signal`.`patient_signal`.`silver_signal_ai_raw`
)
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
  summary_confidence,
  LEFT(feedback_text_safe, 300) AS evidence_excerpt,
  citation_metadata,
  sensitive_data_detected,
  extraction_error,
  CASE
    WHEN extraction_error IS NOT NULL THEN TRUE
    WHEN COALESCE(barrier_confidence, 0) < 0.75 THEN TRUE
    WHEN COALESCE(sentiment_confidence, 0) < 0.75 THEN TRUE
    WHEN COALESCE(urgency_confidence, 0) < 0.75 THEN TRUE
    WHEN sensitive_data_detected THEN TRUE
    ELSE FALSE
  END AS review_required,
  ai_processed_at
FROM parsed;

-- COMMAND ----------
-- MAGIC %md
-- MAGIC ## Holdout evaluation
-- MAGIC Ground-truth labels are joined only after inference. They never enter the
-- MAGIC extraction prompt or the analyst-facing tables.

-- COMMAND ----------

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`validation_ai_extraction_metrics`
COMMENT 'Aggregate exact-match quality metrics on the holdout rows included in the AI sample.'
AS
WITH matched AS (
  SELECT
    s.*,
    g.expected_barrier_category,
    g.expected_sentiment,
    g.expected_urgency
  FROM `patient_signal`.`patient_signal`.`silver_signal_extractions` AS s
  INNER JOIN `patient_signal`.`patient_signal`.`validation_signal_ground_truth` AS g
    ON s.feedback_id = g.feedback_id
)
SELECT
  COUNT(*) AS matched_validation_rows,
  ROUND(AVG(CASE WHEN barrier_category = expected_barrier_category THEN 1.0 ELSE 0.0 END), 4) AS barrier_accuracy,
  ROUND(AVG(CASE WHEN sentiment = expected_sentiment THEN 1.0 ELSE 0.0 END), 4) AS sentiment_accuracy,
  ROUND(AVG(CASE WHEN urgency = expected_urgency THEN 1.0 ELSE 0.0 END), 4) AS urgency_accuracy,
  SUM(CASE WHEN extraction_error IS NOT NULL THEN 1 ELSE 0 END) AS extraction_error_rows,
  ROUND(AVG(CASE WHEN review_required THEN 1.0 ELSE 0.0 END), 4) AS review_rate,
  current_timestamp() AS evaluated_at
FROM matched;

CREATE OR REPLACE TABLE `patient_signal`.`patient_signal`.`validation_barrier_confusion_matrix`
COMMENT 'Expected versus extracted access-barrier counts for prompt review.'
AS
SELECT
  g.expected_barrier_category,
  s.barrier_category AS extracted_barrier_category,
  COUNT(*) AS feedback_count
FROM `patient_signal`.`patient_signal`.`silver_signal_extractions` AS s
INNER JOIN `patient_signal`.`patient_signal`.`validation_signal_ground_truth` AS g
  ON s.feedback_id = g.feedback_id
GROUP BY g.expected_barrier_category, s.barrier_category;

SELECT *
FROM `patient_signal`.`patient_signal`.`validation_ai_extraction_metrics`;

