
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select customer_unique_id as from_field
    from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_sales`
    where customer_unique_id is not null
),

parent as (
    select customer_unique_id as to_field
    from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_customers`
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test