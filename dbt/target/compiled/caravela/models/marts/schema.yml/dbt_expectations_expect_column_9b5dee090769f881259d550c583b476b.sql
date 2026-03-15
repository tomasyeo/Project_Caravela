






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and total_sale_amount >= 0
)
 as expression


    from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_sales`
    

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







