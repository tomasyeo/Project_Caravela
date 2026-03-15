






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and geolocation_lng >= -75 and geolocation_lng <= -34
)
 as expression


    from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_geolocation`
    

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







