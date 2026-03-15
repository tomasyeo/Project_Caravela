






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and date_key >= 2016-01-01 and date_key <= 2018-12-31
)
 as expression


    from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_date`
    

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







