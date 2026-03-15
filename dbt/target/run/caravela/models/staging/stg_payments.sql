

  create or replace view `praxis-paratext-488407-i1`.`olist_analytics`.`stg_payments`
  OPTIONS()
  as WITH source AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_order_payments_dataset_view`
)

SELECT
    CAST(order_id AS STRING) AS order_id,
    CAST(payment_sequential AS INT64) AS payment_sequential,
    CAST(payment_type AS STRING) AS payment_type,
    GREATEST(CAST(payment_installments AS INT64), 1) AS payment_installments,
    CAST(payment_value AS FLOAT64) AS payment_value
FROM source
WHERE CAST(payment_type AS STRING) != 'not_defined';

