-- =====================================================================
--  IslandMart SQL Lab: SQL for data engineers (Day 6)
-- =====================================================================
--  HOW TO USE THIS FILE (in DBeaver)
--  - Open it in DBeaver's SQL editor, connected to your islandmart database.
--  - Put your cursor inside ONE query and press Ctrl+Enter to run just that query.
--  - Write your answer under each "-- your query here" line.
--  - Each exercise has a CHECK line so you can tell if you're right
--    without looking at answers.sql. Only open answers.sql after trying.
--
--  BEFORE YOU START
--  1. Your containers must be running:   docker compose up -d
--  2. Run 00_setup_sales.sql once (it creates the "sales" table).
--
--  YOUR TABLES
--  products  (54 rows)      product_id, name, category, price_mur, stock_qty, last_updated
--  sales     (200,000 rows)  sale_id, sale_date, product_id, quantity, unit_price
--            revenue of one sale = quantity * unit_price
--
--  ONE GOTCHA TO KNOW NOW
--  pandas stored price_mur as "double precision". PostgreSQL's ROUND(x, 2)
--  only works on "numeric", so write ROUND(AVG(price_mur)::numeric, 2).
--  The ::numeric part is a CAST: it converts the value's type.
-- =====================================================================


-- =====================================================================
--  PART 1: CTEs (Common Table Expressions)
-- =====================================================================
--  A CTE gives a name to a query so you can use it like a table:
--
--      WITH my_step AS (
--          SELECT ...            -- step 1
--      )
--      SELECT ... FROM my_step;  -- step 2 uses step 1
--
--  Why data engineers love CTEs: they turn one huge, nested query into
--  readable steps, top to bottom. dbt models (Week 3) are written this way.
--  You can chain several: WITH a AS (...), b AS (...) SELECT ... FROM a JOIN b ...
-- =====================================================================

-- C1. Make a CTE called category_stats with, per category: the number of
--     products and the average price (rounded to 2 decimals). Then select
--     only the categories whose average price is above 100.
--     CHECK: 9 rows. Groceries is first with 672.00.
-- your query here


-- C2. Use TWO CTEs:
--     product_revenue: total revenue per product_id from sales
--     product_names:   one name and category per product_id from products
--                      (hint: product_id 41 appears twice; look up DISTINCT ON)
--     Then join them and show the top 5 products by revenue.
--     CHECK: number 1 is Cooking Oil 2L, revenue 25445250.00.
-- your query here



-- =====================================================================
--  PART 2: WINDOW FUNCTIONS
-- =====================================================================
--  GROUP BY squashes many rows into one row per group.
--  A WINDOW FUNCTION keeps every row, and adds a calculation done over
--  a "window" of related rows. The pattern:
--
--      function() OVER (PARTITION BY ... ORDER BY ... frame)
--
--  PARTITION BY  splits rows into groups (like GROUP BY, but rows stay).
--                Leave it out and the window is the whole result.
--  ORDER BY      the order inside each group (needed for rankings,
--                running totals, LAG/LEAD).
--  frame         which rows around the current one to include,
--                e.g. ROWS BETWEEN 6 PRECEDING AND CURRENT ROW = last 7 rows.
--
--  The functions you'll use:
--  ROW_NUMBER()  1, 2, 3, 4... always unique, even for ties
--  RANK()        ties share a number, then it skips: 1, 2, 2, 4
--  DENSE_RANK()  ties share a number, no skipping:   1, 2, 2, 3
--  SUM/AVG() OVER (...)    totals or averages without collapsing rows
--  LAG(col)      the value from the PREVIOUS row   LEAD(col): the NEXT row
--  NTILE(n)      splits rows into n roughly equal groups
--
--  Rule to remember: you can't use a window function in WHERE.
--  Compute it in a CTE first, then filter on it (you'll see this in W3).
-- =====================================================================

-- W1. ROW_NUMBER: number the products inside each category,
--     most expensive first. Show category, name, price_mur and the number.
--     (Tip: add NULLS LAST after DESC so blank prices go to the bottom.)
--     CHECK: 54 rows. In Condiments, Pâte de Piment 250g is number 1.
-- your query here


-- W2. RANK vs DENSE_RANK: rank ALL products by price, highest first.
--     Show both RANK() and DENSE_RANK() side by side and look at the ties.
--     CHECK: Eggs (Tray of 30) and Shampoo 400ml are both 210 and share rank 10.
--     What number comes next in each column, and why is it different?
-- your query here


-- W3. Top 3 most expensive products in EACH category.
--     (Classic interview question. Use W1 inside a CTE, then filter.)
--     CHECK: 37 rows.
-- your query here


-- W4. DEDUPLICATION (the most common window-function job in data engineering)
--     product_id 41 appears twice. Keep ONE row per product_id: number the
--     rows within each product_id (newest last_updated first, then by name),
--     and keep only number 1.
--     CHECK: 53 rows, and product_id 41 is Carrots 1kg.
-- your query here


-- W5. Show each product's price, its category's average price, and the
--     difference between the two. (AVG ... OVER (PARTITION BY ...))
--     CHECK: 54 rows; every product in the same category shows the same average.
-- your query here


-- W6. Each product's share of its category's total stock, as a percentage
--     with 1 decimal. (stock_qty divided by SUM(stock_qty) OVER (...))
--     Tip: multiply by 100.0 (not 100) so you don't get integer division,
--     and use NULLIF(x, 0) so a category with 0 stock doesn't divide by zero.
--     CHECK: inside each category, the percentages add up to about 100.
-- your query here


-- W7. RUNNING TOTAL: build a CTE "daily" with revenue per sale_date from
--     sales. Then show each day's revenue and the running total for the year.
--     CHECK: 291 rows. The last running total is 116894183.00
--            (the same as SUM of all revenue: a good self-test).
-- your query here


-- W8. MOVING AVERAGE: using the same "daily" CTE, show each day's revenue
--     and its 7-day moving average (this day + the 6 days before).
--     CHECK: on 2026-01-08 the moving average is 407777.57.
--     Why are the first 6 days' averages different from a "real" 7-day average?
-- your query here


-- W9. LAG: show each day's revenue, the previous day's revenue, the change,
--     and the % change (1 decimal).
--     CHECK: on 2026-01-02 the previous day is 343603.00.
--            What does the first row show for "previous day", and why?
-- your query here


-- W10. MONTH-OVER-MONTH: build a CTE "monthly" with revenue per month
--      (DATE_TRUNC('month', sale_date)). Show each month's revenue, its
--      growth % vs the previous month, and its rank by revenue.
--      Tip: name the month column with AS month (without AS, you get an error).
--      CHECK: 10 rows. March 2026 is rank 1 with 12563509.00.
-- your query here


-- BONUS. NTILE: total revenue per product, then split the products into
--        4 groups (quartiles) by revenue. Group 1 = the top 25%.
-- your query here



-- =====================================================================
--  PART 3: UPSERTS (INSERT ... ON CONFLICT, and MERGE)
-- =====================================================================
--  UPSERT = UPDATE the row if it already exists, INSERT it if it doesn't.
--  Pipelines use upserts so they can re-run safely: loading the same data
--  twice must not create duplicates (IDEMPOTENCY again).
--
--  It needs a UNIQUE key (usually the PRIMARY KEY) so Postgres can tell
--  "this row already exists":
--
--      INSERT INTO t (id, value) VALUES (...)
--      ON CONFLICT (id) DO NOTHING;               -- skip existing rows
--
--      ON CONFLICT (id) DO UPDATE
--      SET value = EXCLUDED.value;                -- overwrite existing rows
--
--  EXCLUDED = the row you TRIED to insert (the new values).
--
--  MERGE (PostgreSQL 15+) does the same job with a more general syntax:
--      MERGE INTO target USING source ON <match condition>
--      WHEN MATCHED THEN UPDATE ...
--      WHEN NOT MATCHED THEN INSERT ...
--
--  Compare with your load_products.py: if_exists="replace" rebuilds the
--  whole table every time. An upsert changes only the rows that changed,
--  which is what you want when tables get big.
-- =====================================================================

-- U0. Setup (run as is): a stock table with one row per product.
DROP TABLE IF EXISTS product_stock;
CREATE TABLE product_stock (
    product_id  INT PRIMARY KEY,
    stock_qty   INT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- U1. Try a plain INSERT of every product's product_id and stock_qty
--     from products. It should FAIL. Read the error: which product causes it?
-- your query here


-- U2. Same INSERT, but add ON CONFLICT so rows whose product_id already
--     exists are skipped.
--     CHECK: SELECT count(*) FROM product_stock;  gives 53.
-- your query here


-- U3. A delivery arrives: product 1 now has 150, product 2 has 55, and a
--     brand-new product 999 has 10. Write ONE statement (VALUES list) that
--     updates 1 and 2, inserts 999, and sets updated_at = now().
--     CHECK: 54 rows in product_stock; product 1 shows 150.
-- your query here


-- U4. Do the same kind of job with MERGE: product 1 -> 175, new product 1000 -> 20.
--     (Tip: USING (VALUES (1, 175), (1000, 20)) AS s(product_id, stock_qty))
--     CHECK: 55 rows; product 1 shows 175.
-- your query here


-- U5. Smart upsert: send (1, 175) and (2, 60). Make the UPDATE happen only
--     when the stock value actually changed. Hint: add
--     WHERE product_stock.stock_qty IS DISTINCT FROM EXCLUDED.stock_qty
--     CHECK: product 1's updated_at does NOT change (175 was already there);
--            product 2's does.
-- your query here



-- =====================================================================
--  PART 4: INDEXES AND EXPLAIN
-- =====================================================================
--  EXPLAIN ANALYZE <query> runs the query and shows HOW Postgres did it.
--  Read the plan from the most indented line upwards. Look for:
--
--  Seq Scan            read EVERY row of the table (fine for small tables
--                      or when most rows match; slow for big filtered reads)
--  Index Scan /
--  Bitmap Index Scan   used an index to jump to the matching rows
--  cost=0.00..3971.00  the planner's estimate (startup..total), in made-up units
--  rows=3760           how many rows it EXPECTED
--  actual time=...     real milliseconds; rows=3910 is how many it REALLY got
--  Rows Removed by Filter: 196090   rows it read and then threw away
--  Execution Time      total real time
--
--  An INDEX is like the index at the back of a book: instead of reading
--  every page to find "pineapple", you look it up and jump to the page.
--  Costs: indexes take disk space, and every INSERT/UPDATE must update them
--  too. So you index the columns you FILTER or JOIN on often, not everything.
--  (A PRIMARY KEY gets an index automatically.)
-- =====================================================================

-- E1. Run this and read the plan. Note: the scan type, Rows Removed by
--     Filter, and Execution Time.
EXPLAIN ANALYZE SELECT * FROM sales WHERE product_id = 7;
--     CHECK: Seq Scan, about 196,000 rows removed by the filter.


-- E2. Create an index on sales(product_id), run ANALYZE sales; and then
--     run the SAME EXPLAIN ANALYZE again. What changed?
--     CHECK: Bitmap Index Scan on your index, and a lower Execution Time.
-- your statements here


-- E3. Do the same for a one-week date range:
--     EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date BETWEEN '2026-03-01' AND '2026-03-07';
--     First without an index on sale_date, then create one and compare.
-- your statements here


-- E4. When an index is NOT used (important!). Run both and compare plans:
--     (a) EXPLAIN ANALYZE SELECT * FROM sales WHERE EXTRACT(MONTH FROM sale_date) = 3;
--     (b) EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date >= '2026-03-01' AND sale_date < '2026-04-01';
--     Same rows, different plans. Why can't (a) use your sale_date index?
--     Then try:
--     (c) EXPLAIN ANALYZE SELECT * FROM sales WHERE sale_date >= '2026-02-01';
--     It ignores the index even though it could use it. Why?
--     (Hint: how many of the 200,000 rows match?)
-- your statements here


-- =====================================================================
--  WHEN YOU'RE DONE
--  Write 3-5 lines in your README under "What I learned in SQL":
--  - in your own words: RANK vs DENSE_RANK, and what EXCLUDED means
--  - your E1 vs E2 execution times
--  - your answer to E4: why the index wasn't used
-- =====================================================================
