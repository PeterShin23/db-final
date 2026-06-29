from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


CATALOG = "patient_signal"
SCHEMA = "patient_signal"
TABLE_PREFIX = f"`{CATALOG}`.`{SCHEMA}`"
DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "dashboard.json"


class DataAccessError(RuntimeError):
    """Raised when the analyst-safe Gold data cannot be loaded."""


def backend_name() -> str:
    return os.getenv("DATA_BACKEND", "warehouse").strip().lower()


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _fetch_rows(cursor: Any, sql_text: str, parameters: dict[str, Any] | None = None) -> list[dict]:
    cursor.execute(sql_text, parameters=parameters or {})
    columns = [column[0] for column in cursor.description]
    return [
        {name: _json_value(value) for name, value in zip(columns, row)}
        for row in cursor.fetchall()
    ]


def _matches_dimension(row: dict, therapy: str, region: str, payer_type: str) -> bool:
    return (
        (therapy == "All" or row.get("therapy") == therapy)
        and (region == "All" or row.get("region") == region)
        and (payer_type == "All" or row.get("payer_type") == payer_type)
    )


def _load_snapshot(
    *, therapy: str, region: str, payer_type: str, start_date: date
) -> dict:
    snapshot_path = Path(os.getenv("APP_JSON_PATH", str(DEFAULT_SNAPSHOT_PATH)))
    if not snapshot_path.exists():
        raise DataAccessError(
            f"DATA_BACKEND=json but the Gold snapshot does not exist at {snapshot_path}. "
            "Run notebook 05_export_app_snapshot.py and copy dashboard.json into app-3/data/."
        )

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataAccessError(f"The Gold snapshot at {snapshot_path} is unreadable.") from exc

    signal_metrics = [
        row
        for row in snapshot.get("gold_signal_metrics", [])
        if _matches_dimension(row, therapy, region, payer_type)
        and str(row.get("feedback_month", ""))[:10] >= start_date.isoformat()
    ]
    signal_detail = [
        row
        for row in snapshot.get("gold_signal_detail", [])
        if _matches_dimension(row, therapy, region, payer_type)
        and str(row.get("feedback_timestamp", ""))[:10] >= start_date.isoformat()
    ]
    access_metrics = [
        row
        for row in snapshot.get("gold_access_metrics", [])
        if _matches_dimension(row, therapy, region, payer_type)
    ]

    barrier_groups: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0.0, "weighted_confidence": 0.0, "review": 0.0}
    )
    for row in signal_metrics:
        barrier = str(row.get("barrier_category") or "unclassified")
        count = float(row.get("signal_count") or 0)
        barrier_groups[barrier]["count"] += count
        barrier_groups[barrier]["weighted_confidence"] += (
            float(row.get("average_barrier_confidence") or 0) * count
        )
        barrier_groups[barrier]["review"] += float(row.get("review_required_count") or 0)

    barriers = [
        {
            "barrier_category": barrier,
            "signal_count": int(values["count"]),
            "average_confidence": round(
                values["weighted_confidence"] / values["count"], 3
            ) if values["count"] else 0,
            "review_required_count": int(values["review"]),
        }
        for barrier, values in barrier_groups.items()
    ]
    barriers.sort(key=lambda row: row["signal_count"], reverse=True)

    monthly: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "patients": 0.0,
            "started": 0.0,
            "weighted_days": 0.0,
            "value": 0.0,
        }
    )
    for row in access_metrics:
        month = str(row.get("prescription_month", ""))[:10]
        patients = float(row.get("patient_count") or 0)
        monthly[month]["patients"] += patients
        monthly[month]["started"] += float(row.get("treatment_started_count") or 0)
        monthly[month]["weighted_days"] += float(row.get("median_days_to_outcome") or 0) * patients
        monthly[month]["value"] += float(row.get("annual_value_at_risk_usd") or 0)

    access_trend = [
        {
            "prescription_month": month,
            "patient_count": int(values["patients"]),
            "treatment_start_rate": round(
                values["started"] / values["patients"], 4
            ) if values["patients"] else 0,
            "median_days_to_outcome": round(
                values["weighted_days"] / values["patients"], 1
            ) if values["patients"] else 0,
            "annual_value_at_risk_usd": round(values["value"], 2),
        }
        for month, values in sorted(monthly.items())
    ]

    urgency_rank = {"high": 0, "medium": 1, "low": 2}
    signal_detail.sort(
        key=lambda row: (
            not bool(row.get("review_required")),
            urgency_rank.get(str(row.get("urgency")), 3),
            float(row.get("barrier_confidence") or 0),
        )
    )

    all_signal_metrics = snapshot.get("gold_signal_metrics", [])
    return {
        "meta": {
            "backend": "json-snapshot",
            "is_snapshot": True,
            "generated_at": snapshot.get("exported_at") or datetime.now(timezone.utc).isoformat(),
            "disclosure": "Synthetic POC data • Gold-table JSON snapshot • Verify before client use",
        },
        "filters": {
            "therapies": ["All", *sorted({str(row["therapy"]) for row in all_signal_metrics})],
            "regions": ["All", *sorted({str(row["region"]) for row in all_signal_metrics})],
            "payer_types": ["All", *sorted({str(row["payer_type"]) for row in all_signal_metrics})],
            "selected": {
                "therapy": therapy,
                "region": region,
                "payer_type": payer_type,
                "start_date": start_date.isoformat(),
            },
        },
        "impact": snapshot["gold_business_impact"][0],
        "cohorts": snapshot.get("gold_cohort_comparison", []),
        "barriers": barriers,
        "access_trend": access_trend,
        "evidence": signal_detail[:50],
        "review_required_count": sum(
            1 for row in signal_detail if bool(row.get("review_required"))
        ),
    }


def _load_from_databricks(
    *, therapy: str, region: str, payer_type: str, start_date: date
) -> dict:
    try:
        from databricks import sql
        from databricks.sdk.core import Config
    except ImportError as exc:
        raise DataAccessError(
            "Databricks SQL dependencies are unavailable. Install requirements.txt."
        ) from exc

    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        raise DataAccessError(
            "DATABRICKS_WAREHOUSE_ID is missing. Attach a SQL warehouse resource "
            "with the key 'sql-warehouse'."
        )

    filters = {
        "therapy": therapy,
        "region": region,
        "payer_type": payer_type,
        "start_date": start_date.isoformat(),
    }
    filter_sql = """
      (:therapy = 'All' OR therapy = :therapy)
      AND (:region = 'All' OR region = :region)
      AND (:payer_type = 'All' OR payer_type = :payer_type)
    """

    cfg = Config()
    try:
        connection = sql.connect(
            server_hostname=cfg.host,
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
            credentials_provider=lambda: cfg.authenticate,
        )
        with connection:
            with connection.cursor() as cursor:
                impact_rows = _fetch_rows(
                    cursor,
                    f"SELECT * FROM {TABLE_PREFIX}.`gold_business_impact` LIMIT 1",
                )
                cohorts = _fetch_rows(
                    cursor,
                    f"""
                    SELECT cohort, patient_count, treatment_started_count,
                           treatment_abandoned_count, treatment_start_rate,
                           median_days_to_outcome, annual_value_at_risk_usd
                    FROM {TABLE_PREFIX}.`gold_cohort_comparison`
                    ORDER BY cohort
                    """,
                )
                barriers = _fetch_rows(
                    cursor,
                    f"""
                    SELECT barrier_category,
                           SUM(signal_count) AS signal_count,
                           ROUND(
                             SUM(average_barrier_confidence * signal_count) /
                             NULLIF(SUM(signal_count), 0), 3
                           ) AS average_confidence,
                           SUM(review_required_count) AS review_required_count
                    FROM {TABLE_PREFIX}.`gold_signal_metrics`
                    WHERE {filter_sql} AND feedback_month >= :start_date
                    GROUP BY barrier_category
                    ORDER BY signal_count DESC
                    """,
                    filters,
                )
                access_trend = _fetch_rows(
                    cursor,
                    f"""
                    SELECT prescription_month,
                           SUM(patient_count) AS patient_count,
                           ROUND(SUM(treatment_started_count) /
                             NULLIF(SUM(patient_count), 0), 4) AS treatment_start_rate,
                           ROUND(SUM(median_days_to_outcome * patient_count) /
                             NULLIF(SUM(patient_count), 0), 1) AS median_days_to_outcome,
                           SUM(annual_value_at_risk_usd) AS annual_value_at_risk_usd
                    FROM {TABLE_PREFIX}.`gold_access_metrics`
                    WHERE {filter_sql}
                    GROUP BY prescription_month
                    ORDER BY prescription_month
                    """,
                    filters,
                )
                evidence = _fetch_rows(
                    cursor,
                    f"""
                    SELECT feedback_id, feedback_timestamp, source, speaker_type,
                           therapy, region, payer_type, barrier_category,
                           barrier_confidence, sentiment, sentiment_confidence,
                           urgency, urgency_confidence, signal_summary,
                           evidence_excerpt, review_required
                    FROM {TABLE_PREFIX}.`gold_signal_detail`
                    WHERE {filter_sql}
                      AND CAST(feedback_timestamp AS DATE) >= :start_date
                    ORDER BY review_required DESC, urgency ASC,
                             barrier_confidence ASC, feedback_timestamp DESC
                    LIMIT 50
                    """,
                    filters,
                )
                review_rows = _fetch_rows(
                    cursor,
                    f"""
                    SELECT COUNT(*) AS review_required_count
                    FROM {TABLE_PREFIX}.`gold_signal_detail`
                    WHERE {filter_sql}
                      AND CAST(feedback_timestamp AS DATE) >= :start_date
                      AND review_required = TRUE
                    """,
                    filters,
                )
                option_rows = _fetch_rows(
                    cursor,
                    f"""
                    SELECT ARRAY_SORT(COLLECT_SET(therapy)) AS therapies,
                           ARRAY_SORT(COLLECT_SET(region)) AS regions,
                           ARRAY_SORT(COLLECT_SET(payer_type)) AS payer_types
                    FROM {TABLE_PREFIX}.`gold_signal_metrics`
                    """,
                )
    except Exception as exc:
        raise DataAccessError(
            "The Gold tables could not be queried. Confirm that the app service "
            "principal can use the SQL warehouse and SELECT the patient_signal Gold tables."
        ) from exc

    if not impact_rows:
        raise DataAccessError("gold_business_impact returned no rows.")

    options = option_rows[0] if option_rows else {}
    return {
        "meta": {
            "backend": "databricks-sql",
            "is_snapshot": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclosure": "Synthetic POC data • Live governed Gold tables • Verify before client use",
        },
        "filters": {
            "therapies": ["All", *(options.get("therapies") or [])],
            "regions": ["All", *(options.get("regions") or [])],
            "payer_types": ["All", *(options.get("payer_types") or [])],
            "selected": filters,
        },
        "impact": impact_rows[0],
        "cohorts": cohorts,
        "barriers": barriers,
        "access_trend": access_trend,
        "evidence": evidence,
        "review_required_count": (
            review_rows[0].get("review_required_count", 0) if review_rows else 0
        ),
    }


def load_dashboard(
    *, therapy: str, region: str, payer_type: str, start_date: date
) -> dict:
    selected_backend = backend_name()
    if selected_backend == "warehouse":
        return _load_from_databricks(
            therapy=therapy,
            region=region,
            payer_type=payer_type,
            start_date=start_date,
        )
    if selected_backend == "json":
        return _load_snapshot(
            therapy=therapy,
            region=region,
            payer_type=payer_type,
            start_date=start_date,
        )
    raise DataAccessError(
        f"Unsupported DATA_BACKEND={selected_backend!r}. Use 'warehouse' or 'json'."
    )

