{{ config(
    materialized='incremental',
    unique_key='sale_id',
    incremental_strategy='delete+insert'
) }}

with sales as (
    select * from {{ ref('int_sales_with_customer_versions') }}

    {% if is_incremental() %}
    -- only sales newer than the latest one already in this table
    where sale_id > (select max(sale_id) from {{ this }})
    {% endif %}
)

select
    sale_id,
    {{ date_key('sale_date') }}                           as date_key,
    product_id                                            as product_key,
    store_id                                              as store_key,
    customer_version_id                                   as customer_key,
    quantity,
    unit_price_mur,
    cast(quantity * unit_price_mur as decimal(12, 2))     as sales_amount_mur,
    current_timestamp                                     as dbt_loaded_at
from sales