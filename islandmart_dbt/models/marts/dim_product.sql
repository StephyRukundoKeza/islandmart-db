select
    product_id      as product_key,
    product_id,
    product_name,
    category,
    price_mur,
    stock_qty,
    last_updated
from {{ ref('stg_islandmart__products') }}