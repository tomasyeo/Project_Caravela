
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select order_status
from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_orders`
where order_status is null



  
  
      
    ) dbt_internal_test