
    
    

with child as (
    select product_id as from_field
    from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_sales`
    where product_id is not null
),

parent as (
    select product_id as to_field
    from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_products`
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


