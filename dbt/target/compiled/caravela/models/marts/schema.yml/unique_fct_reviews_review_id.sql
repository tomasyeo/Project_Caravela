
    
    

with dbt_test__target as (

  select review_id as unique_field
  from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_reviews`
  where review_id is not null

)

select
    unique_field,
    count(*) as n_records

from dbt_test__target
group by unique_field
having count(*) > 1


