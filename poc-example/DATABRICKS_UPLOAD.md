# Upload the Patient Signal Workbench data to Databricks

For this POC, use a Unity Catalog managed volume as the landing location for
the raw CSV and JSON files. Do not upload them directly as final tables; the
notebooks will create the bronze, silver, and gold tables.

## 1. Choose the catalog and schema

In Databricks, open **Catalog** and identify a catalog where you can create a
schema. Do not assume a catalog name. Record these values:

```text
CATALOG = ____________________
SCHEMA  = ____________________
VOLUME  = patient_signal_files
```

For a disposable POC, `patient_signal` is a reasonable schema name if you have
permission to create it.

## 2. Create the schema and managed volume

Open a SQL editor or SQL notebook and replace `YOUR_CATALOG` and `YOUR_SCHEMA`
before running:

```sql
CREATE SCHEMA IF NOT EXISTS `YOUR_CATALOG`.`YOUR_SCHEMA`;

CREATE VOLUME IF NOT EXISTS
  `YOUR_CATALOG`.`YOUR_SCHEMA`.`patient_signal_files`
COMMENT 'Synthetic landing files for the MedPulse Patient Signal Workbench POC';
```

If this fails with `PERMISSION_DENIED`, use an existing schema or ask for
`USE CATALOG`, `USE SCHEMA`, and `CREATE VOLUME` privileges.

## 3. Upload the files

The browser upload is the shortest path for Databricks Free Edition:

1. In the left sidebar, select **New** > **Add or upload data**.
2. Select **Upload files to a volume**.
3. Select the volume created above.
4. Create a directory named `raw` and upload all five files from
   `poc/.data/raw/`.
5. Create a directory named `validation` and upload
   `poc/.data/validation/signal_ground_truth.csv`.
6. Upload `poc/.data/manifest.json` to the volume root.

The resulting location should look like:

```text
/Volumes/YOUR_CATALOG/YOUR_SCHEMA/patient_signal_files/
├── manifest.json
├── raw/
│   ├── analyst_annotations_raw.csv
│   ├── feedback_raw.jsonl
│   ├── journey_events_raw.csv
│   ├── patients_raw.csv
│   └── therapy_reference.csv
└── validation/
    └── signal_ground_truth.csv
```

## 4. Verify the upload

Replace the catalog and schema placeholders and run:

```sql
LIST '/Volumes/YOUR_CATALOG/YOUR_SCHEMA/patient_signal_files/raw/';

SELECT COUNT(*) AS patient_rows
FROM read_files(
  '/Volumes/YOUR_CATALOG/YOUR_SCHEMA/patient_signal_files/raw/patients_raw.csv',
  format => 'csv',
  header => true,
  inferSchema => true
);

SELECT COUNT(*) AS journey_rows
FROM read_files(
  '/Volumes/YOUR_CATALOG/YOUR_SCHEMA/patient_signal_files/raw/journey_events_raw.csv',
  format => 'csv',
  header => true,
  inferSchema => true
);

SELECT COUNT(*) AS feedback_rows
FROM read_files(
  '/Volumes/YOUR_CATALOG/YOUR_SCHEMA/patient_signal_files/raw/feedback_raw.jsonl',
  format => 'json'
);
```

Expected results:

| Check | Expected |
|---|---:|
| Patients | 5,000 |
| Journey events | 30,000 |
| Feedback | 4,000 |

Keep the full volume path. The first notebook will use it as its only required
configuration value.

## Permissions used later

The notebook author needs `READ VOLUME` on the volume plus permission to create
tables in the target schema. The analyst-facing app should receive access only
to the de-identified silver and aggregated gold tables, not the raw volume.

Reference: [Databricks on AWS: upload and verify volume files](https://docs.databricks.com/aws/en/volumes/unstructured-data-tutorial)

