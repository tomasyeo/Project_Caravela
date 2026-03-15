
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select order_id
from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_reviews`
where order_id is null



  
  
      
    ) dbt_internal_test