-- ELT transform: build the clean table from the raw JSON, inside Postgres
CREATE TABLE IF NOT EXISTS supplier_products_elt (
    product_id   INT PRIMARY KEY,
    title        TEXT NOT NULL,
    category     TEXT NOT NULL,
    brand        TEXT NOT NULL,
    price        NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    discount_pct NUMERIC(5,2),
    rating       NUMERIC(3,2),
    stock        INT CHECK (stock >= 0),
    availability TEXT,
    sku          TEXT,
    updated_at   TIMESTAMPTZ NOT NULL
);

TRUNCATE supplier_products_elt;

INSERT INTO supplier_products_elt
SELECT DISTINCT ON (product_id)
    product_id,
    TRIM(data ->> 'title')                                    AS title,
    data ->> 'category'                                       AS category,
    COALESCE(NULLIF(TRIM(data ->> 'brand'), ''), 'Unknown')   AS brand,
    ROUND(CAST(data ->> 'price' AS numeric), 2)               AS price,
    ROUND(CAST(data ->> 'discountPercentage' AS numeric), 2)  AS discount_pct,
    CAST(data ->> 'rating' AS numeric)                        AS rating,
    CAST(data ->> 'stock' AS int)                             AS stock,
    data ->> 'availabilityStatus'                             AS availability,
    data ->> 'sku'                                            AS sku,
    CAST(data -> 'meta' ->> 'updatedAt' AS timestamptz)       AS updated_at
FROM raw.supplier_products
ORDER BY product_id, updated_at DESC;