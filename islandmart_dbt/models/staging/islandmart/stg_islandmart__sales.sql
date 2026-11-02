with source as (
    select * from {{ source('islandmart', 'sales') }}
)

select
    sale_id,
    cast(sale_date as date)            as sale_date,
    product_id,
    customer_id,
    store_id,
    cast(quantity as integer)          as quantity,
    cast(unit_price as decimal(10, 2)) as unit_price_mur
from source