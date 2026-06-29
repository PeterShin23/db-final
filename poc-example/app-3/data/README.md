# Optional Gold JSON snapshot

The app queries the Databricks SQL warehouse by default. This directory is used
only when `DATA_BACKEND=json` is explicitly configured.

To create the fallback snapshot:

1. Run `poc/notebooks/05_export_app_snapshot.py` in Databricks.
2. Download `dashboard.json` from:
   `/Volumes/patient_signal/patient_signal/patient_signal_files/app_export/`
3. Place it at `poc/app-3/data/dashboard.json`.
4. Set `DATA_BACKEND=json` in `app.yaml`.

The snapshot contains only Gold tables. It must never include Bronze direct
identifiers or raw feedback text.

