






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and payment_value >= 0
)
 as expression


    from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_payments`
    

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







