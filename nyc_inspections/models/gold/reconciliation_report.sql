-- Reconciliation report: compares row counts across all layers
-- Helps detect data loss or duplication between pipeline stages

WITH bronze_count AS (
    SELECT
        COUNT(*)                    AS bronze_rows,
        MAX(dbt_loaded_at)          AS last_loaded_at
    FROM {{ source('raw', 'inspections_bronze') }}
),

silver_count AS (
    SELECT
        COUNT(*)                    AS silver_rows,
        MAX(inspection_date)        AS last_inspection_date
    FROM {{ ref('silver_inspections') }}
),

gold_kpi_count AS (
    SELECT COUNT(*) AS gold_kpi_rows
    FROM {{ ref('gold_department_kpi') }}
),

gold_compliance_count AS (
    SELECT COUNT(*) AS gold_compliance_rows
    FROM {{ ref('gold_compliance_rates_by_borough') }}
)

SELECT
    b.bronze_rows,
    s.silver_rows,
    g.gold_kpi_rows,
    c.gold_compliance_rows,

    -- Data loss check: how many rows were filtered in silver
    b.bronze_rows - s.silver_rows          AS rows_filtered_in_silver,

    -- Filter rate percentage
    ROUND(
        (b.bronze_rows - s.silver_rows)
        * 100.0 / NULLIF(b.bronze_rows, 0),
        2
    )                                       AS silver_filter_rate_pct,

    -- Pipeline health flag
    CASE
        WHEN s.silver_rows >= b.bronze_rows * 0.5
        THEN 'HEALTHY'
        ELSE 'WARNING - High filter rate'
    END                                     AS pipeline_health,

    b.last_loaded_at                        AS bronze_last_loaded,
    s.last_inspection_date                  AS silver_last_date,
    NOW()                                   AS report_generated_at

FROM bronze_count b
CROSS JOIN silver_count s
CROSS JOIN gold_kpi_count g
CROSS JOIN gold_compliance_count c
