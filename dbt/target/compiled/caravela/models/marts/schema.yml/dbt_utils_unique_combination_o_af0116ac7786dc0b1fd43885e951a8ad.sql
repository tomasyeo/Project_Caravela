





with validation_errors as (

    select
        order_id, payment_sequential
    from `praxis-paratext-488407-i1`.`olist_analytics`.`fct_payments`
    group by order_id, payment_sequential
    having count(*) > 1

)

select *
from validation_errors


