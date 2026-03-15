WITH source AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_orders_dataset_view`
)

SELECT
    CAST(order_id AS STRING) AS order_id,
    CAST(customer_id AS STRING) AS customer_id,
    CAST(order_status AS STRING) AS order_status,
    SAFE_CAST(order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
    SAFE_CAST(order_approved_at AS TIMESTAMP) AS order_approved_at,
    SAFE_CAST(order_delivered_carrier_date AS TIMESTAMP) AS order_delivered_carrier_date,
    SAFE_CAST(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
    SAFE_CAST(order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date,
    DATE(SAFE_CAST(order_purchase_timestamp AS TIMESTAMP)) AS date_key
FROM source