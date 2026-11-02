with source as (
    select * from {{ source('islandmart', 'products') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by product_id
            order by last_updated desc nulls last, name
        ) as row_num
    from source
)

select
    product_id,
    trim(name)                         as product_name,
    category,
    cast(price_mur as decimal(10, 2))  as price_mur,
    cast(stock_qty as integer)         as stock_qty,
    cast(last_updated as date)         as last_updated
from ranked
-- one product_id appears twice in the raw data: keep the most recently updated row
where row_num = 1