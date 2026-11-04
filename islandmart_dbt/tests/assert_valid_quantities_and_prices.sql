-- Every sale must have a positive quantity and a price above zero.
select sale_id, quantity, unit_price_mur
from {{ ref('stg_islandmart__sales') }}
where quantity <= 0
   or unit_price_mur <= 0

   