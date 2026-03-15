
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select price
from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_order_items`
where price is null



  
  
      
    ) dbt_internal_test