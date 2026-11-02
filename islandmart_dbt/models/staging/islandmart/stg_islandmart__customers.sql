with source as (
    select * from {{ source('islandmart', 'customers') }}
)

select
    customer_id,
    md5(lower(trim(email)))  as email_hash,
    town,
    district,
    loyalty_tier,
    updated_at
from source
-- first_name, last_name and phone are dropped on purpose: personal data analytics doesn't need