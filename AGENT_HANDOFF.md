
# 1.1 Planning and Data Set up

 I would mock four raw datasets totaling about 40,000 rows. That is large enough to show meaningful trends but small enough for Free Edition and a
  four-hour build.

  ## Recommended dataset

   Raw dataset                  Rows    Purpose
  ━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   patients_raw                5,000    Demonstrate sensitive-data governance and de-identification
  ─────────────────────────  ────────  ─────────────────────────────────────────────────────────────────
   journey_events_raw         30,000    Show progression from prescription through treatment initiation
  ─────────────────────────  ────────  ─────────────────────────────────────────────────────────────────
   feedback_raw                4,000    Provide unstructured text for AI extraction
  ─────────────────────────  ────────  ─────────────────────────────────────────────────────────────────
   analyst_annotations_raw       200    Demonstrate analyst review and human oversight
  ─────────────────────────  ────────  ─────────────────────────────────────────────────────────────────
   signal_ground_truth           500    Measure whether AI extraction is accurate
  ─────────────────────────  ────────  ─────────────────────────────────────────────────────────────────
   Total                      39,700

  ### 1. Patient profiles

  Use 5,000 entirely synthetic patients.

  Include:

  - Synthetic patient/member ID
  - Synthetic name
  - Date of birth
  - ZIP code
  - Region
  - Payer type
  - Therapy
  - Diagnosis date

  The sensitive fields should exist only in the restricted bronze layer. Silver should replace them with:

  - Surrogate patient key
  - Age band
  - Broad geographic region
  - Payer category

  Do not generate SSNs or detailed medical histories. They add risk and no demo value.

  ### 2. Patient journey events

  Generate approximately six events per patient, or 30,000 rows.

  Possible events:

  1. Prescription written
  2. Prior authorization submitted
  3. Authorization approved or denied
  4. Appeal submitted
  5. Specialty pharmacy contacted
  6. Treatment started or abandoned

  Important fields:

  - Patient key
  - Event date
  - Therapy
  - Journey stage
  - Outcome
  - Delay in days
  - Payer type
  - Region
  - Abandonment reason

  ### 3. Unstructured feedback

  Generate 4,000 realistic text records from only two sources:

  - Call-center transcripts: 2,500
  - Patient or physician survey responses: 1,500

  Each record should contain:

  - Feedback ID
  - Date
  - Source
  - Patient or provider key where applicable
  - Free text
  - Therapy
  - Region
  - Payer type

  Some records should deliberately contain synthetic identifiers so the pipeline can demonstrate masking.

  The AI workflow should derive—not mock—the following:

  - Barrier category
  - Sentiment
  - Urgency
  - Journey stage
  - Concise summary
  - Supporting evidence excerpt
  - Confidence
  - Review-required flag

  ### 4. Analyst annotations

  Create around 200 annotations representing human review:

  - Accepted AI classification
  - Corrected barrier
  - Analyst note
  - Review status
  - Review timestamp

  This demonstrates that AI assists analysts rather than silently replacing their judgment.

  ## The business story embedded in the data

  Avoid random, evenly distributed data. Inject one discoverable problem:

  > During the final eight weeks, commercially insured patients in the Northeast using Therapy A experience a sharp rise in prior-authorization and
  > specialty-pharmacy delays.

  Example pattern:

  - Median time to treatment increases from 8 to 18 days.
  - Treatment initiation falls from 76% to 58%.
  - Negative access-related feedback triples.
  - Approximately 200–300 patient starts become at risk.

  This lets the application answer:

  - What are people saying?
  - What is the likely cause?
  - What should the analyst recommend?
  Only bronze data should be mocked. Silver and gold should be produced by the notebooks.

  Bronze
  ├── patients_raw
  ├── journey_events_raw
  ├── feedback_raw
  └── analyst_annotations_raw

  Silver
  ├── patients_deidentified
  ├── journey_events_curated
  ├── feedback_masked
  └── signal_extractions

  Gold
  ├── access_barrier_summary
  ├── treatment_start_metrics
  └── client_ready_insights

  I would explicitly exclude claims, full EHR records, CRM campaigns, social media, and MSL notes from the first prototype. Adding them would
  broaden the demo without strengthening the central proof.

  