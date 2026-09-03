WITH ranked_violations AS (
    SELECT
        violation_code,
        violation_description,
        department_category,
        DATE_TRUNC('month', inspection_date)    AS inspection_month,
        COUNT(*)                                AS violation_count,
        SUM(CASE WHEN critical_flag = 'Critical'
            THEN 1 ELSE 0 END)                  AS critical_count
    FROM {{ ref('silver_inspections') }}
    WHERE
        violation_code IS NOT NULL
        AND inspection_date >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY
        violation_code, violation_description,
        department_category,
        DATE_TRUNC('month', inspection_date)
),
top_violations AS (
    SELECT violation_code
    FROM ranked_violations
    GROUP BY violation_code
    ORDER BY SUM(violation_count) DESC
    LIMIT 10
)
SELECT r.*
FROM ranked_violations r
INNER JOIN top_violations t ON r.violation_code = t.violation_code
ORDER BY r.violation_count DESC, r.inspection_month
