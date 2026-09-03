SELECT
    camis, dba, boro, building, street, zipcode, phone,
    cuisine_description, inspection_date, action,
    violation_code, violation_description, critical_flag,
    score, grade, grade_date, record_date, inspection_type,
    latitude, longitude, community_board, council_district,
    census_tract, bin, bbl, nta,
    dbt_loaded_at, pipeline_batch_id,
    NOW() AS dbt_updated_at
FROM {{ source('raw', 'inspections_bronze') }}
