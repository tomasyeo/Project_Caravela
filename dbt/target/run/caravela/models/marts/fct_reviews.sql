
  
    

    create or replace table `praxis-paratext-488407-i1`.`olist_analytics`.`fct_reviews`
      
    
    

    
    OPTIONS()
    as (
      SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    date_key,
    review_answer_timestamp
FROM `praxis-paratext-488407-i1`.`olist_analytics`.`stg_reviews`
    );
  