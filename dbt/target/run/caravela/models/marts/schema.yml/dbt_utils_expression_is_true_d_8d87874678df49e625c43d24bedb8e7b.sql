
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  



select
    1
from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_date`

where not(date_key date_key >= cast('2016-01-01' as date) and date_key <= cast('2018-12-31' as date))


  
  
      
    ) dbt_internal_test