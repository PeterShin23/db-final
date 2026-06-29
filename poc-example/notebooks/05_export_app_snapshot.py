# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — Export app JSON snapshot
# MAGIC
# MAGIC Optional fallback only. The Patient Signal Workbench normally queries
# MAGIC the SQL warehouse directly. Run this notebook if app service-principal
# MAGIC permissions cannot be resolved in time for the demo.
# MAGIC
# MAGIC The snapshot includes analyst-safe Gold tables only. No Bronze direct
# MAGIC identifiers or raw feedback text are exported.

# COMMAND ----------

import json
from datetime import datetime, timezone

CATALOG = "patient_signal"
SCHEMA = "patient_signal"
OUTPUT_PATH = (
    "/Volumes/patient_signal/patient_signal/"
    "patient_signal_files/app_export/dashboard.json"
)


def rows_as_json(table_name: str, order_by: list[str] | None = None) -> list[dict]:
    dataframe = spark.table(f"{CATALOG}.{SCHEMA}.{table_name}")
    if order_by:
        dataframe = dataframe.orderBy(*order_by)
    # These are small Gold presentation tables. Serializing them on the driver is
    # deliberate so the app receives one portable JSON document.
    return [json.loads(row.value) for row in dataframe.toJSON().collect()]


snapshot = {
    "format_version": 1,
    "exported_at": datetime.now(timezone.utc).isoformat(),
    "source_catalog": CATALOG,
    "source_schema": SCHEMA,
    "gold_business_impact": rows_as_json("gold_business_impact"),
    "gold_cohort_comparison": rows_as_json("gold_cohort_comparison", ["cohort"]),
    "gold_access_metrics": rows_as_json(
        "gold_access_metrics",
        ["prescription_month", "therapy", "region", "payer_type"],
    ),
    "gold_signal_metrics": rows_as_json(
        "gold_signal_metrics",
        ["feedback_month", "therapy", "region", "payer_type", "barrier_category"],
    ),
    "gold_signal_detail": rows_as_json(
        "gold_signal_detail",
        ["feedback_timestamp", "feedback_id"],
    ),
}

dbutils.fs.mkdirs(OUTPUT_PATH.rsplit("/", 1)[0])
dbutils.fs.put(OUTPUT_PATH, json.dumps(snapshot, separators=(",", ":")), overwrite=True)

display(
    spark.createDataFrame(
        [
            ("gold_business_impact", len(snapshot["gold_business_impact"])),
            ("gold_cohort_comparison", len(snapshot["gold_cohort_comparison"])),
            ("gold_access_metrics", len(snapshot["gold_access_metrics"])),
            ("gold_signal_metrics", len(snapshot["gold_signal_metrics"])),
            ("gold_signal_detail", len(snapshot["gold_signal_detail"])),
        ],
        ["dataset", "exported_rows"],
    )
)
print(f"Snapshot written to {OUTPUT_PATH}")

