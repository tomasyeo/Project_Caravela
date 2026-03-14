SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    date_key,
    review_answer_timestamp
FROM {{ ref('stg_reviews') }}
