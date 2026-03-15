WITH order_items AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_order_items`
),

orders AS (
    SELECT
        order_id,
        customer_id,
        order_status,
        date_key,
        order_delivered_customer_date,
        order_estimated_delivery_date
    FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_orders`
),

customers AS (
    SELECT
        customer_id,
        customer_unique_id
    FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_customers`
)

SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    c.customer_unique_id,
    o.date_key,
    o.order_status,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value AS total_sale_amount,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date
FROM order_items oi
JOIN orders o
    ON oi.order_id = o.order_id
JOIN customers c
    ON o.customer_id = c.customer_id