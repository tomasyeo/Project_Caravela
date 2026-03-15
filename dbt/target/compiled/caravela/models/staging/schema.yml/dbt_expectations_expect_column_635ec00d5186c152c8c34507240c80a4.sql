





    with grouped_expression as (
    select
        
        
    
  order_delivered_carrier_date >= order_approved_at as expression


    from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_orders`
    

),
validation_errors as (

    select
        *
    from
        grouped_expression
    where
        not(expression = true)

)

select *
from validation_errors




