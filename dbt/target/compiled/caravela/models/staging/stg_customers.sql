WITH source AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_customers_dataset_view`
)

SELECT
    CAST(customer_id AS STRING) AS customer_id,
    CAST(customer_unique_id AS STRING) AS customer_unique_id,
    CAST(customer_zip_code_prefix AS STRING) AS customer_zip_code_prefix,
    CAST(customer_city AS STRING) AS customer_city,
    CAST(customer_state AS STRING) AS customer_state
FROM source