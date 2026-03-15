
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select customer_unique_id
from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_sales`
where customer_unique_id is null



  
  
      
    ) dbt_internal_test