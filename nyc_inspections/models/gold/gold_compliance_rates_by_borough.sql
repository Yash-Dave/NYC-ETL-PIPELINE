SELECT
    borough,
    grade,
    COUNT(*)                                    AS inspection_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY borough),
        2
    )                                           AS grade_percentage,
    DATE_TRUNC('month', inspection_date)        AS inspection_month
FROM {{ ref('silver_inspections') }}
WHERE
    inspection_date >= CURRENT_DATE - INTERVAL '12 months'
    AND grade IN ('A','B','C')
GROUP BY
    borough, grade,
    DATE_TRUNC('month', inspection_date)
ORDER BY borough, inspection_month
