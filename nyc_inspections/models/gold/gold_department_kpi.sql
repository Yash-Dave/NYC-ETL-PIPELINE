SELECT
    department_category,
    COUNT(DISTINCT camis)                       AS unique_restaurants,
    COUNT(*)                                    AS total_inspections,
    COUNT(violation_code)                       AS total_violations,
    ROUND(
        SUM(CASE WHEN critical_flag = 'Critical' THEN 1 ELSE 0 END)
        * 100.0 / NULLIF(COUNT(*), 0), 2
    )                                           AS critical_violation_rate,
    ROUND(AVG(inspection_score), 1)             AS avg_inspection_score,
    ROUND(
        SUM(CASE WHEN is_grade_a THEN 1 ELSE 0 END)
        * 100.0 / NULLIF(COUNT(*), 0), 2
    )                                           AS grade_a_rate,
    MAX(inspection_date)                        AS last_inspection_date
FROM {{ ref('silver_inspections') }}
WHERE inspection_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY department_category
ORDER BY total_violations DESC
