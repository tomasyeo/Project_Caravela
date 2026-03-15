
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  





    with grouped_expression as (
    select
        
        
    
  order_delivered_customer_date >= order_delivered_carrier_date as expression


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





  
  
      
    ) dbt_internal_test