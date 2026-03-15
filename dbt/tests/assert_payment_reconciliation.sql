-- tests/assert_payment_reconciliation.sql
-- Payment totals and sales totals should reconcile within R$20.00 per order
-- for single-installment orders only.
--
-- Calibration notes (evidence from live BigQuery, 2026-03-15):
--   - 236 multi-installment orders excluded: Olist payment_value includes
--     credit card interest (parcelamento com juros), which inflates payment_total
--     above price + freight_value. This is expected, not a data defect.
--   - 13 single-installment orders have diffs up to R$16.50 (avg R$6.15):
--     minor freight-subsidy anomalies in the Olist source data. Threshold
--     set to R$20.00 to accommodate these known outliers while still catching
--     model bugs (wrong JOIN, double-counting) which would produce 10x+ errors.
--
-- Zero rows = test passes.
SELECT order_id, ABS(payment_total - sales_total) AS diff
FROM (
  SELECT
    fp.order_id,
    SUM(fp.payment_value) AS payment_total,
    fs.order_total AS sales_total
  FROM {{ ref('fct_payments') }} fp
  JOIN (
    SELECT order_id, SUM(total_sale_amount) AS order_total
    FROM {{ ref('fct_sales') }}
    GROUP BY order_id
  ) fs USING (order_id)
  GROUP BY fp.order_id, fs.order_total
  HAVING ABS(SUM(fp.payment_value) - fs.order_total) > 20.00
    AND MAX(fp.payment_installments) = 1
)
