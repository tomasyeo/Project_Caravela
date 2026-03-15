WITH source AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`product_category_name_translation_view`
)

SELECT
    CAST(product_category_name AS STRING) AS product_category_name,
    CAST(product_category_name_english AS STRING) AS product_category_name_english
FROM source