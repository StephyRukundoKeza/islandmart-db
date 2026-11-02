with sales as (
    select * from {{ ref('int_sales_with_customer_versions') }}
)

select
    sale_id,
    cast(strftime(sale_date, '%Y%m%d') as integer)        as date_key,
    product_id                                            as product_key,
    store_id                                              as store_key,
    customer_version_id                                   as customer_key,
    quantity,
    unit_price_mur,
    cast(quantity * unit_price_mur as decimal(12, 2))     as sales_amount_mur
from sales