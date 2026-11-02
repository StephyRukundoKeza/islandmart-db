select
    store_id        as store_key,
    store_id,
    store_name,
    town,
    district,
    store_type
from {{ ref('stores') }}