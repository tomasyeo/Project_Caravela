WITH payments AS (
    SELECT * FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_payments`
),

orders AS (
    SELECT
        order_id,
        date_key
    FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_orders`
)

SELECT
    p.order_id,
    p.payment_sequential,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    o.date_key
FROM payments p
LEFT JOIN orders o
    ON p.order_id = o.order_id