

  create or replace view `praxis-paratext-488407-i1`.`olist_analytics`.`stg_products`
  OPTIONS()
  as WITH products AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_products_dataset_view`
),

translations AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`product_category_name_translation_view`
)

SELECT
    CAST(p.product_id AS STRING) AS product_id,
    CAST(p.product_category_name AS STRING) AS product_category_name,
    COALESCE(
        CAST(t.product_category_name_english AS STRING),
        CASE
            WHEN TRIM(IFNULL(CAST(p.product_category_name AS STRING), '')) = '' THEN NULL
            ELSE CAST(p.product_category_name AS STRING)
        END,
        'uncategorized'
    ) AS product_category_name_english,
    SAFE_CAST(p.product_name_lenght AS INT64) AS product_name_length,
    SAFE_CAST(p.product_description_lenght AS INT64) AS product_description_length,
    SAFE_CAST(p.product_photos_qty AS INT64) AS product_photos_qty,
    SAFE_CAST(p.product_weight_g AS INT64) AS product_weight_g,
    SAFE_CAST(p.product_length_cm AS FLOAT64) AS product_length_cm,
    SAFE_CAST(p.product_height_cm AS FLOAT64) AS product_height_cm,
    SAFE_CAST(p.product_width_cm AS FLOAT64) AS product_width_cm
FROM products p
LEFT JOIN translations t
    ON CAST(p.product_category_name AS STRING) = CAST(t.product_category_name AS STRING);

