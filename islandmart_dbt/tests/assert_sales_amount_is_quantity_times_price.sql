-- Fails if any order line's amount isn't quantity x unit price, or is negative.
select sale_id, quantity, unit_price_mur, sales_amount_mur
from {{ ref('fct_orders') }}
where sales_amount_mur <> quantity * unit_price_mur
   or sales_amount_mur < 0