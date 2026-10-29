with tags as (
    select * from {{ source('dummyjson', 'products__tags') }}
),

products as (
    select product_id, dlt_id from {{ ref('stg_dummyjson__products') }}
)

select
    products.product_id,
    tags.value as tag
from tags
join products on tags._dlt_parent_id = products.dlt_id