# Patient Signal Workbench — application and demo specification

## Purpose

The Patient Signal Workbench should prove that MedPulse can turn fragmented
healthcare data and AI workflows into a governed, analyst-facing application
without a long handoff from data science to application engineering.

The application's single job is to help a life-sciences analyst answer:

> Why are treatment starts deteriorating for a specific patient cohort, what
> evidence explains the change, and where should the client intervene?

This keeps the prototype focused on a business decision rather than presenting
Databricks as a collection of platform features.

## Does the prototype support the proposed narrative?

Yes, with one important qualification.

The prototype supports these two pain points:

1. **Fragmented data and AI workflows make it difficult to assemble a complete
   patient-access signal.** The prototype combines patient profiles, journey
   events, call-center feedback, surveys, analyst annotations, and therapy
   reference data into one governed model.
2. **Useful analytics remain trapped in data pipelines and notebooks for too
   long.** The Gold tables are already shaped for direct use by a secure
   analyst application, removing another custom data-preparation handoff.

The qualification is that the POC does not connect to MedPulse's real S3,
Snowflake, CRM, Tableau, or SageMaker environments. It demonstrates the target
consolidation pattern using synthetic files. The presentation should describe
this as a working target-state proof, not a completed platform migration.

The strongest framing is therefore not simply "the data is all over the place."
It is:

> Patient signals and AI workflows are distributed across systems and technical
> teams, so analysts cannot independently turn them into timely, governed client
> advice.

## Business story supported by the Gold layer

The synthetic scenario contains a deliberate access deterioration affecting
Therapy A patients with commercial insurance in the Northeast beginning in May
2026.

Expected executive results from `gold_business_impact` and
`gold_cohort_comparison` are:

| Metric | Affected cohort | Comparison |
|---|---:|---:|
| Treatment-start rate | 56.5% | 76.0% |
| Median days to outcome | 18 | 8 |
| Excess patient starts at risk | 117 | — |
| Estimated incremental annual value at risk | $2.106M | — |

For the affected cohort, the AI signal results shown in the completed Gold query
are:

| Barrier | Signals | Average confidence |
|---|---:|---:|
| Prior authorization | 139 | 0.944 |
| Specialty-pharmacy delay | 74 | 0.950 |
| Out-of-pocket cost | 34 | 0.953 |
| Payer denial | 31 | 0.946 |
| Step therapy | 13 | 0.950 |
| No barrier | 10 | 0.935 |
| Scheduling | 7 | 0.944 |

This supports the recommendation already encoded in the Gold layer:

> Investigate prior-authorization and specialty-pharmacy workflows with
> Northeast commercial payers.

## Intended user

The primary user is a life-sciences analyst or client-facing consultant. The
interface should use business language such as "treatment starts," "access
barriers," and "evidence." It should not expose table names, Spark terminology,
model endpoints, or medallion terminology during the normal analyst workflow.

## Application scope

The initial POC is a read-only analytics application backed by the Gold tables.
It demonstrates exploration and review, but does not persist new analyst
annotations.

Before implementation, choose the data-access pattern:

| Pattern | Use in this POC | Tradeoff |
|---|---|---|
| Databricks Apps Analytics | Recommended | Direct Gold-table queries; appropriate for KPIs, charts, filters, and browsing |
| Analytics plus Lakebase | Optional extension | Required only if new analyst annotations must be saved during the demo |

## Information architecture

Use one workspace with three analyst-facing sections and one global architecture
control:

```text
Patient Signal Workbench
├── Overview
│   ├── Business impact
│   ├── Cohort comparison
│   └── Recommended action
├── Explore signals
│   ├── Filters
│   ├── Barrier distribution
│   ├── Access trend
│   └── Evidence results
├── Review queue
│   ├── Low-confidence or sensitive-source records
│   └── Evidence detail panel
└── How this works
    └── Full-page architecture and medallion-flow dialog
```

The navigation labels should describe analyst tasks. "How this works" is the
only place that should explain platform architecture.

## Screen 1 — Overview

### Purpose

Answer "What changed, how large is the impact, and what should we investigate?"
within the first ten seconds.

### Components

1. **Business signal headline**
   - Therapy A — Northeast commercial access deterioration
   - Supporting copy: "Treatment starts are 19.5 percentage points below the
     comparison cohort."
2. **Impact strip**
   - 56.5% affected treatment-start rate
   - 18 median days to outcome
   - 117 excess patient starts at risk
   - $2.106M estimated annual value at risk
3. **Cohort comparison**
   - Two horizontal bars comparing treatment-start rates
   - A compact comparison for median days to outcome
   - Avoid gauges; a direct baseline-versus-affected comparison is clearer
4. **Recommended action**
   - "Investigate prior-authorization and specialty-pharmacy workflows with
     Northeast commercial payers."
   - Primary action: `Explore supporting signals`
5. **Scope disclosure**
   - "Synthetic POC data • AI sample: 1,000 feedback records"

### Gold sources

- `patient_signal.patient_signal.gold_business_impact`
- `patient_signal.patient_signal.gold_cohort_comparison`

## Screen 2 — Explore signals

### Purpose

Explain why the business metric changed and let the analyst inspect supporting
market evidence.

### Filters

- Date range
- Therapy
- Region
- Payer type
- Feedback source
- Barrier
- Sentiment
- Urgency

Default the initial demo state to:

```text
Therapy: Therapy A
Region: Northeast
Payer: Commercial
Date: May 2026 onward
```

Always display active filters next to the chart title so the user cannot mistake
a filtered cohort for the whole population.

### Components

1. **Barrier distribution**
   - Descending horizontal bar chart
   - Prior authorization and specialty-pharmacy delay should be visibly dominant
   - Show signal count and average confidence in the tooltip
2. **Access trend**
   - Monthly treatment-start rate and median days to outcome
   - Use separate aligned charts rather than combining incompatible units on a
     dual axis
3. **Sentiment and urgency summary**
   - Compact stacked bar or segmented counts
   - These are supporting context, not the hero chart
4. **Evidence results**
   - Summary
   - Barrier
   - Sentiment
   - Urgency
   - Confidence
   - Review status
   - Source and timestamp
5. **Evidence detail drawer**
   - Masked source excerpt
   - AI summary
   - Confidence for barrier, sentiment, and urgency
   - Explicit label: "AI-assisted — verify before client use"

### Gold sources

- `patient_signal.patient_signal.gold_signal_metrics`
- `patient_signal.patient_signal.gold_access_metrics`
- `patient_signal.patient_signal.gold_signal_detail`

Limit detailed query results to a small page, such as 25 records, to keep the app
responsive and below analytics response-size limits.

## Screen 3 — Review queue

### Purpose

Show that the workflow is governed and that uncertain AI results are reviewable
rather than silently treated as fact.

### Components

1. Count of records requiring review
2. Filterable list where `review_required = true`
3. Confidence values and masked evidence
4. Reason for review:
   - Low confidence
   - Sensitive source content was masked
   - Extraction error, if present
5. For the read-only POC, use a disabled or demonstration-only `Confirm signal`
   action with copy explaining that persisted write-back is a production next
   step

### Gold source

- `patient_signal.patient_signal.gold_signal_detail`

If persisted confirmation or correction is required, add Lakebase and replace
the demonstration-only action with an actual annotation workflow.

## Full-page architecture dialog

Provide a global `How this works` button. It should open a full-page dialog with
a clear close button and the following flow:

```text
Representative source systems
S3 files • Snowflake data • CRM • call center • surveys • analyst notes
                              ↓
Bronze — restricted raw landing
Direct identifiers and original text; engineering access only
                              ↓
Silver — de-identified and curated
Hashed patient keys • masked text • standardized patient journeys
                              ↓
Databricks AI Functions
Barrier • sentiment • urgency • concise summary • confidence • citations
                              ↓
Gold — analyst-safe decision products
Access KPIs • signal trends • evidence detail • business impact
                              ↓
Patient Signal Workbench
Secure self-service analysis through Databricks Apps
```

The dialog must distinguish the POC from a production deployment:

| Element | POC status | Production requirement |
|---|---|---|
| Source data | Synthetic files uploaded to a managed volume | Connect approved S3, Snowflake, CRM, transcript, and survey sources |
| De-identification | Deterministic masking of synthetic identifiers | Privacy-approved rules, tokenization, quality monitoring, and policy testing |
| AI extraction | `ai_extract` over a 1,000-record sample | Full-volume pipeline, evaluation thresholds, monitoring, and exception handling |
| Governance | Bronze/Silver/Gold separation and grant pattern | Identity groups, row/column policies, audit review, retention, and client isolation |
| Application | Read-only analyst experience | SSO groups, operational support, annotation persistence, and release controls |

## Trust and governance behavior

- The app queries Gold tables only.
- Never display patient keys, member IDs, names, dates of birth, phone numbers,
  or raw Bronze text.
- Label AI-derived fields as AI-assisted.
- Display confidence near the extracted value, not in a hidden tooltip only.
- Keep the masked source excerpt available so analysts can verify the summary.
- Make review-required records visually distinct without using alarmist red for
  every item.
- Display the synthetic-data and sample-size disclosure persistently.

## Visual direction

The interface should feel like a patient-signal investigation workspace, not a
generic executive dashboard.

- Use a restrained clinical palette: deep navy for structure, Databricks blue
  for interactive elements, teal for trusted/confirmed signals, amber for
  review-required states, and warm white for the primary surface.
- Make the cohort comparison the signature element: a compact visual "signal
  gap" connecting the 56.5% affected rate to the 76.0% comparison rate.
- Keep cards flat and information-dense; avoid decorative gradients, excessive
  rounded containers, and dashboard-style gauge charts.
- Use one deliberate transition when filters update the evidence panel. Avoid
  ambient animation.
- Maintain keyboard navigation, visible focus, responsive behavior, and reduced
  motion support.

## Table-to-component mapping

| Gold table | App component | Primary fields |
|---|---|---|
| `gold_business_impact` | Impact strip and recommendation | start-rate gap, days, starts at risk, value at risk, recommended action |
| `gold_cohort_comparison` | Affected-versus-comparison chart | cohort, patient count, start rate, median days |
| `gold_access_metrics` | Monthly access trend | month, therapy, region, payer, start rate, delay, value at risk |
| `gold_signal_metrics` | Barrier, sentiment, and urgency summaries | month, dimensions, category, count, average confidence |
| `gold_signal_detail` | Evidence list, detail drawer, review queue | summary, masked excerpt, labels, confidence, review flag |
| `validation_ai_extraction_metrics` | Internal demo-quality disclosure only | validation count, label accuracy, errors, review rate |

The validation table should not be exposed as a normal analyst dataset. Its
metrics can appear in the architecture dialog or presenter notes as evidence
that the AI workflow was evaluated.

## Five-minute demonstration walkthrough

1. **Open on the business outcome.**
   "Therapy A starts for Northeast commercial patients are 19.5 points below
   the comparison group, placing 117 starts and about $2.1M in annual value at
   risk."
2. **Move from what to why.**
   Select `Explore supporting signals`. Prior authorization appears first with
   139 signals, followed by 74 specialty-pharmacy-delay signals.
3. **Inspect the evidence.**
   Open one prior-authorization record. Show its masked excerpt, concise summary,
   urgency, and confidence.
4. **Demonstrate governance.**
   Open the Review queue and explain that low-confidence or previously sensitive
   records are flagged for human verification.
5. **Connect the prototype to the platform decision.**
   Open `How this works` and show how governed source data becomes a reusable
   Gold product and then an internal application without exporting another copy
   of the data.
6. **Close on action.**
   "The analyst now has enough evidence to prioritize payer authorization and
   specialty-pharmacy interventions."

## What the demo proves

- Multiple structured and unstructured source types can feed one governed model.
- Direct identifiers can be separated from analyst-facing data.
- An AI workflow can convert text into reviewable business signals.
- Gold outputs can be reused directly by a secure internal application.
- The analyst can move from a commercial anomaly to evidence and action in one
  experience.

## What the demo does not prove

- Production integration with MedPulse's real systems
- Production-grade PHI de-identification or HIPAA control validation
- Full-scale AI throughput, cost, drift monitoring, or prompt lifecycle
- Persistent annotation write-back
- Measured reduction in MedPulse's real delivery time or operating cost

These should be presented as production next steps, not implied capabilities of
the four-hour prototype.

## SQL verification queries for the presenter

Run these directly in Databricks before finalizing the app copy.

```sql
SELECT *
FROM patient_signal.patient_signal.gold_business_impact;

SELECT *
FROM patient_signal.patient_signal.gold_cohort_comparison
ORDER BY cohort;

SELECT *
FROM patient_signal.patient_signal.validation_ai_extraction_metrics;

SELECT
  barrier_category,
  SUM(signal_count) AS signal_count,
  ROUND(AVG(average_barrier_confidence), 3) AS average_confidence
FROM patient_signal.patient_signal.gold_signal_metrics
WHERE therapy = 'Therapy A'
  AND region = 'Northeast'
  AND payer_type = 'Commercial'
  AND feedback_month >= DATE '2026-05-01'
GROUP BY barrier_category
ORDER BY signal_count DESC;

SELECT
  COUNT(*) AS signal_detail_rows,
  SUM(CASE WHEN review_required THEN 1 ELSE 0 END) AS review_required_rows
FROM patient_signal.patient_signal.gold_signal_detail;
```

If the returned values differ from those documented above, the application and
presentation must use the Databricks query results as the source of truth.

