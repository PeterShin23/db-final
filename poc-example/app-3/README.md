# Patient Signal Workbench

A React + FastAPI Databricks App that turns governed Gold tables into a
self-service patient-access investigation experience for MedPulse analysts.

## Data path

The default and preferred backend is the Databricks SQL warehouse:

```text
Gold Delta tables → SQL warehouse → FastAPI → React
```

The app does not silently fall back to invented data. If warehouse access is
misconfigured, `/api/dashboard` returns a clear `503` error.

An explicit JSON fallback is available for demo recovery:

```text
Gold Delta tables → Notebook 05 → dashboard.json → FastAPI → React
```

## Databricks resource setup

In the Databricks Apps configuration:

1. Add the SQL warehouse as a resource.
2. Set its resource key to `sql-warehouse`.
3. Grant the app service principal `CAN USE` on the warehouse.
4. Grant the app service principal:
   - `USE CATALOG` on `patient_signal`
   - `USE SCHEMA` on `patient_signal.patient_signal`
   - `SELECT` on the five Gold tables used by the app

The app reads:

- `patient_signal.patient_signal.gold_business_impact`
- `patient_signal.patient_signal.gold_cohort_comparison`
- `patient_signal.patient_signal.gold_access_metrics`
- `patient_signal.patient_signal.gold_signal_metrics`
- `patient_signal.patient_signal.gold_signal_detail`

`app.yaml` injects the attached warehouse ID through `valueFrom`; no warehouse
ID or access token is stored in source code.

## Local development

The local app still uses a real data source. Choose one:

### Warehouse

Set Databricks authentication and warehouse variables, then run:

```bash
export DATA_BACKEND=warehouse
export DATABRICKS_WAREHOUSE_ID=<warehouse-id>
pip install -r requirements.txt
npm install
npm run build
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Gold JSON snapshot

1. Run `../notebooks/05_export_app_snapshot.py` in Databricks.
2. Download the generated `dashboard.json` into `data/dashboard.json`.
3. Run:

```bash
export DATA_BACKEND=json
npm install
npm run build
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend-only development

Run the backend on port 8000, then start Vite:

```bash
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to FastAPI.

## Production build

```bash
npm run build
```

Vite writes the frontend bundle to `backend/static`, which FastAPI serves from
the same process. `python -m backend.main` reads `DATABRICKS_APP_PORT` and binds
Uvicorn to `0.0.0.0`.

## Demo path

1. Open on the affected-versus-comparison signal gap.
2. Show 117 starts and approximately $2.1M in annual value at risk.
3. Open the signal explorer and show prior authorization as the primary barrier.
4. Inspect a masked evidence record with confidence and urgency.
5. Open the review queue to demonstrate human oversight.
6. Open **How this works** to explain Bronze → Silver → AI → Gold → App.
