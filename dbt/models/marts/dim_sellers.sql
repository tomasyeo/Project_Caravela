WITH sellers AS (
    SELECT * FROM {{ ref('stg_sellers') }}
),

geo AS (
    SELECT * FROM {{ ref('stg_geolocation') }}
)

SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    s.seller_zip_code_prefix,
    g.geolocation_lat,
    g.geolocation_lng
FROM sellers s
LEFT JOIN geo g
    ON s.seller_zip_code_prefix = g.zip_code_prefix
