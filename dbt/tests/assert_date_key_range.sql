-- tests/assert_date_key_range.sql
-- All date_key values should be within the known data range (2016-01-01 to 2018-12-31).
-- A passing singular test returns zero rows.
SELECT 'fct_sales' AS source_table, date_key
FROM {{ ref('fct_sales') }}
WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'

UNION ALL

SELECT 'fct_reviews', date_key
FROM {{ ref('fct_reviews') }}
WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'

UNION ALL

SELECT 'fct_payments', date_key
FROM {{ ref('fct_payments') }}
WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'
