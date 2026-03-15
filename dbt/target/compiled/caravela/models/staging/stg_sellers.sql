WITH source AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_sellers_dataset_view`
)

SELECT
    CAST(seller_id AS STRING) AS seller_id,
    CAST(seller_zip_code_prefix AS STRING) AS seller_zip_code_prefix,
    CAST(seller_city AS STRING) AS seller_city,
    CAST(seller_state AS STRING) AS seller_state
FROM source