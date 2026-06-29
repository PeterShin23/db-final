# Databricks notebook run order

Import the four `.sql` source files as Databricks notebooks and run them in
numeric order using serverless compute:

1. `01_bronze_ingestion.sql` — source files to restricted managed Delta tables
2. `02_silver_deidentification.sql` — remove direct identifiers and curate journeys
3. `03_ai_signal_extraction.sql` — extract reviewable access signals with AI
4. `04_gold_business_insights.sql` — build app-ready KPIs and business impact

The notebooks are already configured for:

```text
Catalog: patient_signal
Schema:  patient_signal
Volume:  /Volumes/patient_signal/patient_signal/patient_signal_files
```

Notebook 03 uses `ai_extract` version 2.1 and processes 1,000 of the 4,000
feedback records by default. It stores confidence scores, citation metadata,
and a review flag while using only text de-identified by Notebook 02.

Expected final business result:

- Affected cohort start rate: approximately 56.5%
- Comparison start rate: approximately 76.0%
- Median days to outcome: 18 versus 8
- Estimated incremental annual value at risk: approximately $2.106M

