

  create or replace view `praxis-paratext-488407-i1`.`olist_analytics`.`stg_reviews`
  OPTIONS()
  as WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY review_id
            ORDER BY review_answer_timestamp DESC
        ) AS row_num
    FROM `praxis-paratext-488407-i1`.`olist_raw`.`olist_order_reviews_dataset_view`
)

SELECT
    CAST(review_id AS STRING) AS review_id,
    CAST(order_id AS STRING) AS order_id,
    CAST(review_score AS INT64) AS review_score,
    CAST(review_comment_title AS STRING) AS review_comment_title,
    CAST(review_comment_message AS STRING) AS review_comment_message,
    CAST(review_creation_date AS TIMESTAMP) AS review_creation_date,
    CAST(review_answer_timestamp AS TIMESTAMP) AS review_answer_timestamp,
    DATE(CAST(review_creation_date AS TIMESTAMP)) AS date_key
FROM ranked
WHERE row_num = 1;

