WITH source AS (
    SELECT * FROM {{ ref('bronze_inspections') }}
),
cleaned AS (
    SELECT
        TRIM(camis)                         AS camis,
        TRIM(UPPER(dba))                    AS dba,
        INITCAP(TRIM(boro))                 AS borough,
        TRIM(building)                      AS building,
        TRIM(UPPER(street))                 AS street,
        TRIM(zipcode)                       AS zipcode,
        TRIM(phone)                         AS phone,
        TRIM(cuisine_description)           AS cuisine_description,

        -- ── Handle multiple date formats ──────────────────────────
        CASE
            WHEN inspection_date IS NULL THEN NULL
            WHEN inspection_date LIKE '%1900%' THEN NULL
            -- ISO format: 2023-08-01T00:00:00.000
            WHEN inspection_date LIKE '%T%'
            THEN TO_DATE(SPLIT_PART(inspection_date, 'T', 1), 'YYYY-MM-DD')
            -- ISO format without time: 2023-08-01
            WHEN inspection_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN TO_DATE(inspection_date, 'YYYY-MM-DD')
            -- US format: 08/01/2023
            WHEN inspection_date ~ '^\d{2}/\d{2}/\d{4}$'
            THEN TO_DATE(inspection_date, 'MM/DD/YYYY')
            ELSE NULL
        END                                 AS inspection_date,

        -- ── Handle multiple date formats for grade_date ───────────
        CASE
            WHEN grade_date IS NULL THEN NULL
            WHEN grade_date LIKE '%1900%' THEN NULL
            WHEN grade_date LIKE '%T%'
            THEN TO_DATE(SPLIT_PART(grade_date, 'T', 1), 'YYYY-MM-DD')
            WHEN grade_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN TO_DATE(grade_date, 'YYYY-MM-DD')
            WHEN grade_date ~ '^\d{2}/\d{2}/\d{4}$'
            THEN TO_DATE(grade_date, 'MM/DD/YYYY')
            ELSE NULL
        END                                 AS grade_date,

        CASE
            WHEN TRIM(score) ~ '^[0-9]+$'
            THEN TRIM(score)::INTEGER
            ELSE NULL
        END                                 AS inspection_score,
        CASE
            WHEN TRIM(UPPER(grade)) IN ('A','B','C','Z','P','N')
            THEN TRIM(UPPER(grade))
            ELSE 'UNKNOWN'
        END                                 AS grade,
        CASE
            WHEN UPPER(TRIM(critical_flag)) = 'CRITICAL'     THEN 'Critical'
            WHEN UPPER(TRIM(critical_flag)) = 'NOT CRITICAL' THEN 'Not Critical'
            ELSE 'Not Applicable'
        END                                 AS critical_flag,
        TRIM(UPPER(violation_code))         AS violation_code,
        TRIM(violation_description)         AS violation_description,
        TRIM(action)                        AS action,
        TRIM(inspection_type)               AS inspection_type,
        CASE
            WHEN latitude ~ '^-?[0-9]+\.?[0-9]*$'
            THEN latitude::NUMERIC
            ELSE NULL
        END                                 AS latitude,
        CASE
            WHEN longitude ~ '^-?[0-9]+\.?[0-9]*$'
            THEN longitude::NUMERIC
            ELSE NULL
        END                                 AS longitude,
        community_board, council_district, census_tract, nta,
        CASE
            WHEN TRIM(UPPER(violation_code)) IN (
                '02A','02B','02C','02D','02E','02F','02G','02H','02I',
                '03A','03B','03C','03D',
                '04A','04B','04C','04D','04E','04F','04G','04H',
                '04L','04M','04N','04O'
            ) THEN 'Food Safety & Hygiene'
            WHEN TRIM(UPPER(violation_code)) IN (
                '08A','08B','08C','09A','09B','09C',
                '10B','10D','10E','10F'
            ) THEN 'Sanitary Conditions'
            WHEN TRIM(UPPER(violation_code)) IN (
                '15A','15B','15C','15D','15E',
                '15G','15H','15I','15J','15K','15L'
            ) THEN 'Compliance & Permits'
            WHEN violation_code IS NULL THEN 'No Violation'
            ELSE 'General'
        END                                 AS department_category,
        CASE
            WHEN UPPER(TRIM(critical_flag)) = 'CRITICAL'     THEN 3
            WHEN UPPER(TRIM(critical_flag)) = 'NOT CRITICAL' THEN 2
            ELSE 1
        END                                 AS risk_level,
        CASE
            WHEN TRIM(UPPER(grade)) = 'A' THEN TRUE
            ELSE FALSE
        END                                 AS is_grade_a,
        dbt_loaded_at,
        pipeline_batch_id
    FROM source
)
SELECT * FROM cleaned
WHERE inspection_date IS NOT NULL
