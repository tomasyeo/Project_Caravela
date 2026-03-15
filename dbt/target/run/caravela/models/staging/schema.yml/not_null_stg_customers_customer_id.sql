
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select customer_id
from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_customers`
where customer_id is null



  
  
      
    ) dbt_internal_test