WITH customers_deduped AS (
    SELECT
        customer_unique_id,
        customer_city,
        customer_state,
        customer_zip_code_prefix,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY customer_id
        ) AS row_num
    FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_customers`
),

single_customers AS (
    SELECT
        customer_unique_id,
        customer_city,
        customer_state,
        customer_zip_code_prefix
    FROM customers_deduped
    WHERE row_num = 1
),

geo AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_geolocation`
)

SELECT
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    c.customer_zip_code_prefix,
    g.geolocation_lat,
    g.geolocation_lng
FROM single_customers c
LEFT JOIN geo g
    ON c.customer_zip_code_prefix = g.zip_code_prefix