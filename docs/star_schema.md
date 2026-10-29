# IslandMart Star Schema

Grain: one row per product line in a sale.

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_SALES : "date_key"
    DIM_PRODUCT ||--o{ FACT_SALES : "product_key"
    DIM_STORE ||--o{ FACT_SALES : "store_key"
    DIM_CUSTOMER ||--o{ FACT_SALES : "customer_key"

    FACT_SALES {
        BIGINT sales_line_key PK
        INT date_key FK
        INT product_key FK
        INT store_key FK
        INT customer_key FK
        VARCHAR sale_id "degenerate dimension"
        INT quantity
        NUMERIC unit_price
        NUMERIC discount_amount
        NUMERIC sales_amount
    }

    DIM_DATE {
        INT date_key PK "e.g. 20261029"
        DATE full_date
        VARCHAR day_name
        INT month
        VARCHAR month_name
        INT quarter
        INT year
        BOOLEAN is_weekend
        BOOLEAN is_public_holiday
    }

    DIM_PRODUCT {
        INT product_key PK
        VARCHAR product_id "natural key"
        VARCHAR product_name
        VARCHAR category
        VARCHAR brand
        VARCHAR supplier_name
        NUMERIC unit_cost
    }

    DIM_STORE {
        INT store_key PK
        VARCHAR store_id "natural key"
        VARCHAR store_name
        VARCHAR town
        VARCHAR district
        VARCHAR store_type
    }

    DIM_CUSTOMER {
        INT customer_key PK
        VARCHAR customer_id "natural key"
        VARCHAR customer_name
        VARCHAR town
        VARCHAR district
        VARCHAR loyalty_tier
        DATE valid_from "SCD2"
        DATE valid_to "SCD2, 9999-12-31 if current"
        BOOLEAN is_current "SCD2"
    }
```

## Notes
- `sale_id` is a degenerate dimension: no table of its own.
- DIM_CUSTOMER is SCD Type 2: a new row per change, so old sales keep the town the customer lived in at the time.
- No phone numbers or emails are stored (privacy).

![Star schema in Lucidchart](star_schema.png)