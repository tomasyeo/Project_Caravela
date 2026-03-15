
    
    

with dbt_test__target as (

  select date_key as unique_field
  from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_date`
  where date_key is not null

)

select
    unique_field,
    count(*) as n_records

from dbt_test__target
group by unique_field
having count(*) > 1


