with sales as (
    select * from {{ ref('stg_islandmart__sales') }}
),

customer_versions as (
    select
        dbt_scd_id                                          as customer_version_id,
        customer_id,
        dbt_valid_from                                      as valid_from,
        coalesce(dbt_valid_to, timestamptz '9999-12-31')    as valid_to
    from {{ ref('customers_snapshot') }}
)

select
    sales.*,
    customer_versions.customer_version_id
from sales
left join customer_versions
    on  sales.customer_id = customer_versions.customer_id
    and sales.sale_date  >= customer_versions.valid_from
    and sales.sale_date  <  customer_versions.valid_to