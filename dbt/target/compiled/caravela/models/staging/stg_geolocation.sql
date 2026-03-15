WITH source AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_geolocation_dataset_view`
)

SELECT
    CAST(geolocation_zip_code_prefix AS STRING) AS zip_code_prefix,
    AVG(CAST(geolocation_lat AS FLOAT64)) AS geolocation_lat,
    AVG(CAST(geolocation_lng AS FLOAT64)) AS geolocation_lng
FROM source
WHERE CAST(geolocation_lat AS FLOAT64) BETWEEN -35 AND 5
  AND CAST(geolocation_lng AS FLOAT64) BETWEEN -75 AND -34
GROUP BY geolocation_zip_code_prefix