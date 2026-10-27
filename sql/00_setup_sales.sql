-- 00_setup_sales.sql
-- Creates a "sales" table with 200,000 fake sales (Jan 1 - Oct 18, 2026)
-- for the products already in your "products" table.
-- Safe to run again: it drops and recreates the table.

DROP TABLE IF EXISTS sales;

CREATE TABLE sales (
    sale_id     BIGSERIAL PRIMARY KEY,
    sale_date   DATE          NOT NULL,
    product_id  INT           NOT NULL,
    quantity    INT           NOT NULL,
    unit_price  NUMERIC(10,2) NOT NULL
);

SELECT setseed(0.42);   -- same "random" data every time you run this

INSERT INTO sales (sale_date, product_id, quantity, unit_price)
SELECT
    DATE '2026-01-01' + floor(random() * 291)::int,   -- a day between Jan 1 and Oct 18
    p.ids[s.i],
    1 + floor(random() * 5)::int,                      -- 1 to 5 items
    p.prices[s.i]
FROM (
    SELECT g,
           1 + floor(random() * (SELECT count(*) FROM products WHERE price_mur IS NOT NULL))::int AS i
    FROM generate_series(1, 200000) AS g
) AS s
CROSS JOIN (
    SELECT array_agg(product_id ORDER BY product_id, name) AS ids,
           array_agg(price_mur  ORDER BY product_id, name) AS prices
    FROM products
    WHERE price_mur IS NOT NULL
) AS p;

ANALYZE sales;   -- refresh the statistics the query planner uses

SELECT count(*) AS sales_rows, min(sale_date) AS first_day, max(sale_date) AS last_day
FROM sales;
