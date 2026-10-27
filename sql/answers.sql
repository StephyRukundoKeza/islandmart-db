-- =====================================================================
-- IslandMart SQL Lab: ANSWER KEY
-- Open this only AFTER you have tried each exercise yourself.
-- Other correct answers exist: if yours gives the same result, it's right.
-- =====================================================================

-- ---------------------------------------------------------------
-- PART 1: CTEs
-- ---------------------------------------------------------------

-- C1. Categories whose average price is above 100 MUR
WITH category_stats AS (
    SELECT category,
           COUNT(*)                 AS products,
           ROUND(AVG(price_mur)::numeric, 2) AS avg_price
    FROM products
    GROUP BY category
)
SELECT *
FROM category_stats
WHERE avg_price > 100
ORDER BY avg_price DESC;

-- C2. Top 5 products by total revenue, with their names (two CTEs)
WITH product_revenue AS (
    SELECT product_id,
           SUM(quantity * unit_price) AS revenue
    FROM sales
    GROUP BY product_id
),
product_names AS (
    SELECT DISTINCT ON (product_id) product_id, name, category
    FROM products
    ORDER BY product_id, name
)
SELECT n.name, n.category, r.revenue
FROM product_revenue r
JOIN product_names n USING (product_id)
ORDER BY r.revenue DESC
LIMIT 5;

-- ---------------------------------------------------------------
-- PART 2: WINDOW FUNCTIONS
-- ---------------------------------------------------------------

-- W1. Number products inside each category, most expensive first
SELECT category, name, price_mur,
       ROW_NUMBER() OVER (PARTITION BY category ORDER BY price_mur DESC NULLS LAST) AS rn
FROM products
ORDER BY category, rn;

-- W2. RANK vs DENSE_RANK on price (look at the ties)
SELECT name, price_mur,
       RANK()       OVER (ORDER BY price_mur DESC NULLS LAST) AS rnk,
       DENSE_RANK() OVER (ORDER BY price_mur DESC NULLS LAST) AS dense_rnk
FROM products
ORDER BY rnk;

-- W3. Top 3 most expensive products per category
WITH ranked AS (
    SELECT category, name, price_mur,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY price_mur DESC NULLS LAST) AS rn
    FROM products
)
SELECT category, name, price_mur, rn
FROM ranked
WHERE rn <= 3
ORDER BY category, rn;

-- W4. Deduplicate: keep ONE row per product_id (fixes the id 41 problem)
WITH numbered AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY last_updated DESC NULLS LAST, name) AS rn
    FROM products
)
SELECT product_id, name, category, price_mur, stock_qty
FROM numbered
WHERE rn = 1
ORDER BY product_id;

-- W5. Each product's price compared with its category average
SELECT category, name, price_mur,
       ROUND((AVG(price_mur) OVER (PARTITION BY category))::numeric, 2)             AS category_avg,
       ROUND((price_mur - AVG(price_mur) OVER (PARTITION BY category))::numeric, 2) AS diff_from_avg
FROM products
ORDER BY category, diff_from_avg DESC NULLS LAST;

-- W6. Each product's share of its category's total stock (%)
SELECT category, name, stock_qty,
       SUM(stock_qty) OVER (PARTITION BY category) AS category_stock,
       ROUND(100.0 * stock_qty / NULLIF(SUM(stock_qty) OVER (PARTITION BY category), 0), 1) AS pct_of_category
FROM products
ORDER BY category, pct_of_category DESC;

-- W7. Daily revenue with a running total for the year
WITH daily AS (
    SELECT sale_date, SUM(quantity * unit_price) AS revenue
    FROM sales
    GROUP BY sale_date
)
SELECT sale_date, revenue,
       SUM(revenue) OVER (ORDER BY sale_date) AS running_total
FROM daily
ORDER BY sale_date;

-- W8. 7-day moving average of daily revenue
WITH daily AS (
    SELECT sale_date, SUM(quantity * unit_price) AS revenue
    FROM sales
    GROUP BY sale_date
)
SELECT sale_date, revenue,
       ROUND(AVG(revenue) OVER (ORDER BY sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS moving_avg_7d
FROM daily
ORDER BY sale_date;

-- W9. Day-over-day change in revenue (LAG)
WITH daily AS (
    SELECT sale_date, SUM(quantity * unit_price) AS revenue
    FROM sales
    GROUP BY sale_date
)
SELECT sale_date, revenue,
       LAG(revenue) OVER (ORDER BY sale_date)           AS previous_day,
       revenue - LAG(revenue) OVER (ORDER BY sale_date) AS change,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY sale_date))
             / NULLIF(LAG(revenue) OVER (ORDER BY sale_date), 0), 1) AS pct_change
FROM daily
ORDER BY sale_date;

-- W10. Monthly revenue, month-over-month growth, and each month's rank
WITH monthly AS (
    SELECT DATE_TRUNC('month', sale_date)::date AS month,
           SUM(quantity * unit_price)           AS revenue
    FROM sales
    GROUP BY 1
)
SELECT month, revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / LAG(revenue) OVER (ORDER BY month), 1) AS mom_growth_pct,
       RANK() OVER (ORDER BY revenue DESC)            AS revenue_rank
FROM monthly
ORDER BY month;

-- BONUS. Split products into 4 groups by total revenue (NTILE)
WITH product_revenue AS (
    SELECT product_id, SUM(quantity * unit_price) AS revenue
    FROM sales
    GROUP BY product_id
)
SELECT product_id, revenue,
       NTILE(4) OVER (ORDER BY revenue DESC) AS revenue_quartile
FROM product_revenue
ORDER BY revenue DESC;

-- ---------------------------------------------------------------
-- PART 3: UPSERTS
-- ---------------------------------------------------------------

-- U0. Setup: a stock table with a PRIMARY KEY (one row per product)
DROP TABLE IF EXISTS product_stock;
CREATE TABLE product_stock (
    product_id  INT PRIMARY KEY,
    stock_qty   INT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- U1. A plain INSERT of all products FAILS: product_id 41 appears twice
-- INSERT INTO product_stock (product_id, stock_qty)
-- SELECT product_id, stock_qty FROM products;
-- ERROR: duplicate key value violates unique constraint "product_stock_pkey"

-- U2. Insert, skipping rows whose product_id already exists
INSERT INTO product_stock (product_id, stock_qty)
SELECT product_id, stock_qty FROM products
ON CONFLICT (product_id) DO NOTHING;

-- U3. A new delivery: update existing products, insert new ones
INSERT INTO product_stock (product_id, stock_qty)
VALUES (1, 150), (2, 55), (999, 10)
ON CONFLICT (product_id) DO UPDATE
SET stock_qty  = EXCLUDED.stock_qty,
    updated_at = now();

-- U4. The same idea with MERGE
MERGE INTO product_stock AS t
USING (VALUES (1, 175), (1000, 20)) AS s(product_id, stock_qty)
ON t.product_id = s.product_id
WHEN MATCHED THEN
    UPDATE SET stock_qty = s.stock_qty, updated_at = now()
WHEN NOT MATCHED THEN
    INSERT (product_id, stock_qty) VALUES (s.product_id, s.stock_qty);

-- U5. Only update when the value actually changed
INSERT INTO product_stock (product_id, stock_qty)
VALUES (1, 175), (2, 60)
ON CONFLICT (product_id) DO UPDATE
SET stock_qty  = EXCLUDED.stock_qty,
    updated_at = now()
WHERE product_stock.stock_qty IS DISTINCT FROM EXCLUDED.stock_qty;

SELECT * FROM product_stock WHERE product_id IN (1, 2, 999, 1000) ORDER BY product_id;

-- ---------------------------------------------------------------
-- PART 4: INDEXES AND EXPLAIN
-- ---------------------------------------------------------------

-- E1. Before an index
DROP INDEX IF EXISTS idx_sales_product_id;
DROP INDEX IF EXISTS idx_sales_sale_date;
EXPLAIN ANALYZE SELECT * FROM sales WHERE product_id = 7;

-- E2. Add an index, refresh stats, run again
CREATE INDEX idx_sales_product_id ON sales (product_id);
ANALYZE sales;
EXPLAIN ANALYZE SELECT * FROM sales WHERE product_id = 7;

-- E3. Date range: one week, before and after an index on sale_date
EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date BETWEEN '2026-03-01' AND '2026-03-07';
CREATE INDEX idx_sales_sale_date ON sales (sale_date);
ANALYZE sales;
EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date BETWEEN '2026-03-01' AND '2026-03-07';

-- E4. When the index is NOT used
-- (a) A function wrapped around the column hides it from the index:
EXPLAIN ANALYZE SELECT * FROM sales WHERE EXTRACT(MONTH FROM sale_date) = 3;
--     Rewrite as a plain range so the index can be used:
EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date >= '2026-03-01' AND sale_date < '2026-04-01';
-- (b) Most of the table matches, so reading everything is cheaper:
EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date >= '2026-02-01';
