{{ config(severity='warn') }}

-- Warning only: products in the catalogue that have never been sold.
-- Worth checking, but not a reason to stop the pipeline.
select p.product_key, p.product_name
from {{ ref('dim_product') }} p
left join {{ ref('fct_orders') }} f using (product_key)
where f.product_key is null