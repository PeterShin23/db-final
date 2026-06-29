# Patient Signal Workbench synthetic data

All people, identifiers, events, feedback, and financial values in this folder
are fictional and were generated for the MedPulse prototype.

## Business pattern

The data contains one intentional signal to discover:

- Cohort: Therapy A, Northeast, Commercial payer, prescribed on or after 2026-05-01
- Treatment-start rate: 56.5% for the cohort versus 76.0% for the comparison group
- Median time to outcome: 18 days versus 8 days
- Prior-authorization share of feedback: 43.8% versus 15.3%
- Estimated excess starts at risk: 117
- Estimated incremental annual value at risk: $2,106,000

These values are recorded in `manifest.json` and validated by the generator.

## Files

| File | Rows | Purpose |
|---|---:|---|
| `raw/patients_raw.csv` | 5,000 | Synthetic patient profiles, including deliberately sensitive fields for the de-identification demo |
| `raw/journey_events_raw.csv` | 30,000 | Six access and treatment events per patient |
| `raw/feedback_raw.jsonl` | 4,000 | Call-center and survey text for masking and AI signal extraction |
| `raw/analyst_annotations_raw.csv` | 200 | Historical human labels for review and comparison |
| `raw/therapy_reference.csv` | 3 | Fictional therapy metadata and annual value assumptions |
| `validation/signal_ground_truth.csv` | 500 | Hidden validation labels for measuring extraction quality |
| `manifest.json` | N/A | Dataset metadata, expected counts, distributions, and story metrics |

The validation file should not be exposed to the analyst application or used as
an input to AI extraction. It exists only to evaluate the extracted results.

## Reproduce

From the repository root:

```bash
python3 poc/scripts/generate_mock_data.py
```

The generator uses only the Python standard library and a fixed random seed.

