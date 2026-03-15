





with validation_errors as (

    select
        order_id, order_item_id
    from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_order_items`
    group by order_id, order_item_id
    having count(*) > 1

)

select *
from validation_errors


