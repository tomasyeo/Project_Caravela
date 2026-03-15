
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select product_category_name
from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_product_category_name_translation`
where product_category_name is null



  
  
      
    ) dbt_internal_test