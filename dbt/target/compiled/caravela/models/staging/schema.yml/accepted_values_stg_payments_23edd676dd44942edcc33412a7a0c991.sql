
    
    

with all_values as (

    select
        payment_type as value_field,
        count(*) as n_records

    from `praxis-paratext-488407-i1`.`olist_analytics`.`stg_payments`
    group by payment_type

)

select *
from all_values
where value_field not in (
    'credit_card','boleto','voucher','debit_card'
)


