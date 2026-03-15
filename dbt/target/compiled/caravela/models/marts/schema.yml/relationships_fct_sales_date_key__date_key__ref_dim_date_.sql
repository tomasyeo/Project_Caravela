
    
    

with child as (
    select date_key as from_field
    from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_sales`
    where date_key is not null
),

parent as (
    select date_key as to_field
    from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_date`
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


