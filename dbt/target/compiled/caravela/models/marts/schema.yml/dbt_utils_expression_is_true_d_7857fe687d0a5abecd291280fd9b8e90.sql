



select
    1
from `praxis-paratext-488407-i1`.`olist_analytics`.`dim_date`

where not(date_key >= cast('2016-01-01' as date) and date_key <= cast('2018-12-31' as date))

