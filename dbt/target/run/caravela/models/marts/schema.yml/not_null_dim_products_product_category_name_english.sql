
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select product_category_name_english
from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_products`
where product_category_name_english is null



  
  
      
    ) dbt_internal_test