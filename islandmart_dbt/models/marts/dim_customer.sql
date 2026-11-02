select
    dbt_scd_id              as customer_key,
    customer_id,
    email_hash,
    town,
    district,
    loyalty_tier,
    dbt_valid_from          as valid_from,
    dbt_valid_to            as valid_to,
    dbt_valid_to is null    as is_current
from {{ ref('customers_snapshot') }}