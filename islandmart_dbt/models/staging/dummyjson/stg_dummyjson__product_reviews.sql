with reviews as (
    select * from {{ source('dummyjson', 'products__reviews') }}
),

products as (
    select product_id, dlt_id from {{ ref('stg_dummyjson__products') }}
)

select
    products.product_id,
    reviews._dlt_list_idx + 1        as review_number,
    cast(reviews.rating as integer)  as rating,
    reviews.comment,
    reviews.reviewer_name
    -- reviewer_email is left out on purpose: personal data we don't need
from reviews
join products on reviews._dlt_parent_id = products.dlt_id