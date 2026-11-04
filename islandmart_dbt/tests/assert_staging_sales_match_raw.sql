-- Reconciliation: staging must keep every raw sale (no rows lost or duplicated on the way).
with raw as (
    select count(*) as n from {{ source('islandmart', 'sales') }}
),

stg as (
    select count(*) as n from {{ ref('stg_islandmart__sales') }}
)

select raw.n as raw_rows, stg.n as staging_rows
from raw, stg
where raw.n <> stg.n