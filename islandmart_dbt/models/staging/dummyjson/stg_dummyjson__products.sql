with source as (
    select * from {{ source('dummyjson', 'products') }}
),

renamed as (
    select
        id                                            as product_id,
        trim(title)                                   as title,
        category,
        coalesce(nullif(trim(brand), ''), 'Unknown')  as brand,
        cast(price as decimal(10, 2))                 as price,
        cast(discount_percentage as decimal(5, 2))    as discount_pct,
        cast(rating as decimal(3, 2))                 as rating,
        stock,
        availability_status,
        sku,
        meta__updated_at                              as updated_at,
        _dlt_id                                       as dlt_id
    from source
)

select * from renamed