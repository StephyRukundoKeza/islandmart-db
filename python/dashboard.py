"""IslandMart sales dashboard: reads the dbt marts (fct_orders + dims) from the DuckDB warehouse."""
import os

import duckdb
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "warehouse/islandmart.duckdb")

st.set_page_config(page_title="IslandMart Sales", layout="wide")


@st.cache_data(ttl=300)
def query(sql: str):
    """Run a query on the warehouse (read-only), cached for 5 minutes."""
    with duckdb.connect(DUCKDB_PATH, read_only=True) as con:
        return con.sql(sql).df()


st.title("IslandMart Sales 2026")
st.caption(
    "Built from the dbt marts (fct_orders, dim_date, dim_product, dim_store, dim_customer). "
    "Refreshed daily by Airflow."
)

# 1. Headline numbers
kpis = query("""
    select sum(f.sales_amount_mur)        as revenue,
           count(*)                       as order_lines,
           count(distinct c.customer_id)  as customers
    from main.fct_orders f
    join main.dim_customer c using (customer_key)
""").iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Revenue (MUR)", f"{kpis['revenue']:,.0f}")
col2.metric("Order lines", f"{kpis['order_lines']:,}")
col3.metric("Customers", f"{kpis['customers']:,}")

# 2. Revenue per month
st.subheader("Revenue per month")
monthly = query("""
    select date_trunc('month', d.full_date) as month,
           sum(f.sales_amount_mur)          as revenue_mur
    from main.fct_orders f
    join main.dim_date d using (date_key)
    group by 1
    order by 1
""")
st.line_chart(monthly, x="month", y="revenue_mur")

left, right = st.columns(2)

# 3. Revenue by store district
with left:
    st.subheader("Revenue by store district")
    by_district = query("""
        select s.district, sum(f.sales_amount_mur) as revenue_mur
        from main.fct_orders f
        join main.dim_store s using (store_key)
        group by 1
        order by 2 desc
    """)
    st.bar_chart(by_district, x="district", y="revenue_mur")

# 4. Public holidays vs normal days
with right:
    st.subheader("Average revenue per day")
    holidays = query("""
        select case when d.is_public_holiday then 'Public holiday' else 'Normal day' end as day_type,
               sum(f.sales_amount_mur) / count(distinct d.date_key)                       as avg_revenue_mur
        from main.fct_orders f
        join main.dim_date d using (date_key)
        group by 1
    """)
    st.bar_chart(holidays, x="day_type", y="avg_revenue_mur")

# 5. Top 10 products
st.subheader("Top 10 products by revenue")
top_products = query("""
    select p.product_name, p.category, sum(f.sales_amount_mur) as revenue_mur
    from main.fct_orders f
    join main.dim_product p using (product_key)
    group by 1, 2
    order by 3 desc
    limit 10
""")
st.dataframe(top_products, hide_index=True)