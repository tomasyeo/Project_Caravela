
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  





with validation_errors as (

    select
        order_id, order_item_id
    from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_sales`
    group by order_id, order_item_id
    having count(*) > 1

)

select *
from validation_errors



  
  
      
    ) dbt_internal_test