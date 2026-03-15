
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select payment_type
from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_payments`
where payment_type is null



  
  
      
    ) dbt_internal_test