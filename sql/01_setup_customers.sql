-- 01_setup_customers.sql
-- Adds 500 fake IslandMart customers and links every sale to a customer and a store.


DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id   INT PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT NOT NULL,
    town          TEXT NOT NULL,
    district      TEXT NOT NULL,
    loyalty_tier  TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL
);

SELECT setseed(0.42);   -- same "random" data every time

INSERT INTO customers
SELECT
    r.g,
    a.first_names[r.fi],
    a.last_names[r.li],
    lower(a.first_names[r.fi]) || '.' || lower(a.last_names[r.li]) || r.g || '@example.mu',
    '+230 5' || lpad(floor(random() * 10000000)::int::text, 7, '0'),
    a.towns[r.ti],
    a.districts[r.ti],
    (ARRAY['Bronze', 'Silver', 'Gold'])[1 + floor(random() * 3)::int],
    TIMESTAMPTZ '2025-12-01 00:00:00+04' + r.g * INTERVAL '1 minute'   -- unique, and before the first sale
FROM (
    SELECT g,
           1 + floor(random() * 16)::int AS fi,
           1 + floor(random() * 12)::int AS li,
           1 + floor(random() * 13)::int AS ti
    FROM generate_series(1, 500) AS g
) AS r
CROSS JOIN (
    SELECT
        ARRAY['Aisha','Ravi','Priya','Jean','Marie','Kevin','Anjali','Yusuf',
              'Sophie','Arjun','Chloe','Vikash','Nadia','Luc','Meera','Ibrahim'] AS first_names,
        ARRAY['Appadoo','Chung','Dookhun','Lagesse','Mohit','Ramsamy',
              'Seegoolam','Fong','Hossenbux','Labonne','Bhujun','Perrine']     AS last_names,
        ARRAY['Port Louis','Curepipe','Quatre Bornes','Vacoas','Rose Hill','Pamplemousses',
              'Grand Baie','Goodlands','Flacq','Mahébourg','Souillac','Tamarin','Moka'] AS towns,
        ARRAY['Port Louis','Plaines Wilhems','Plaines Wilhems','Plaines Wilhems','Plaines Wilhems',
              'Pamplemousses','Rivière du Rempart','Rivière du Rempart','Flacq','Grand Port',
              'Savanne','Black River','Moka'] AS districts
) AS a;

-- Link every sale to a customer and a store
ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_id INT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS store_id INT;

UPDATE sales
SET customer_id = 1 + floor(random() * 500)::int,
    store_id    = 1 + floor(random() * 5)::int;

ANALYZE sales;

SELECT (SELECT count(*) FROM customers)                         AS customers,
       (SELECT count(*) FROM sales WHERE customer_id IS NULL)   AS sales_without_customer;