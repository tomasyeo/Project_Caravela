-- tests/assert_boleto_single_installment.sql
-- Boleto payments must have payment_installments = 1.
-- The stg_payments clamp (installments=0→1) should have fixed all violations.
-- A passing singular test returns zero rows.
SELECT order_id, payment_sequential, payment_installments
FROM `praxis-paratext-488407-i1`.`olist_analytics`.`fct_payments`
WHERE payment_type = 'boleto'
  AND payment_installments != 1