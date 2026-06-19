import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Retail Sales Intelligence", layout="wide")
st.title("📊 Retail Sales Intelligence Dashboard")

# --- DATA INTEGRATION WORKAROUND ---
# This looks for files directly in your GitHub folder to avoid the 403 error
sales_path = "retail_weekly_sales.xlsx"
store_path = "store_master.xlsx"

sales_df = None
store_df = None

# Check if files exist on GitHub/Server
if os.path.exists(sales_path) and os.path.exists(store_path):
    sales_df = pd.read_excel(sales_path)
    store_df = pd.read_excel(store_path)
    st.success("✅ Data loaded automatically from repository!")
else:
    st.sidebar.header("📂 Data Upload")
    sales_file = st.sidebar.file_uploader("Upload Weekly Sales Data", type=['xlsx'])
    store_file = st.sidebar.file_uploader("Upload Store Master Data", type=['xlsx'])
    if sales_file and store_file:
        sales_df = pd.read_excel(sales_file)
        store_df = pd.read_excel(store_file)

if sales_df is not None and store_df is not None:
    # Standardize names
    sales_df.columns = sales_df.columns.str.strip().str.lower()
    store_df.columns = store_df.columns.str.strip().str.lower()

    # Merge
    df = pd.merge(sales_df, store_df, on='store_id', how='left', suffixes=('', '_drop'))
    df = df.loc[:,~df.columns.str.contains('_drop')]
    df['week_start_date'] = pd.to_datetime(df['week_start_date'], errors='coerce')

    # --- FILTERS ---
    st.sidebar.header("🔍 Filters")
    region = st.sidebar.multiselect("Region", sorted(df['region'].unique()), default=df['region'].unique())
    cat = st.sidebar.multiselect("Category", sorted(df['product_category'].unique()), default=df['product_category'].unique())
    
    filtered_df = df[(df['region'].isin(region)) & (df['product_category'].isin(cat))]

    # --- KPIs ---
    net_sales = filtered_df['net_sales'].sum()
    target = filtered_df['sales_target'].sum()
    ach = (net_sales/target*100) if target > 0 else 0
    atv = net_sales / filtered_df['transactions'].sum() if filtered_df['transactions'].sum() > 0 else 0
    ret_rate = (filtered_df['returns_amount'].sum() / net_sales * 100) if net_sales > 0 else 0
    disc_rate = (filtered_df['discount_amount'].sum() / filtered_df['gross_sales'].sum() * 100) if filtered_df['gross_sales'].sum() > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Net Sales", f"₹{net_sales:,.0f}")
    c2.metric("Target Achievement", f"{ach:.1f}%")
    c3.metric("ATV", f"₹{atv:,.0f}")
    c4.metric("Return Rate", f"{ret_rate:.1f}%")
    c5.metric("Discount Rate", f"{disc_rate:.1f}%")

    # --- CHARTS ---
    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Weekly Trend")
        trend = filtered_df.groupby('week_start_date')['net_sales'].sum().reset_index()
        st.plotly_chart(px.line(trend, x='week_start_date', y='net_sales'), use_container_width=True)
        
        st.subheader("Category Performance")
        st.plotly_chart(px.pie(filtered_df, values='net_sales', names='product_category'), use_container_width=True)

    with col_right:
        st.subheader("Sales by Region")
        st.plotly_chart(px.bar(filtered_df.groupby('region')['net_sales'].sum().reset_index(), x='region', y='net_sales'), use_container_width=True)
        
        st.subheader("Top 10 Stores")
        top_stores = filtered_df.groupby('store_name')['net_sales'].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(top_stores, x='net_sales', y='store_name', orientation='h'), use_container_width=True)

    # --- INSIGHTS ---
    st.subheader("💡 AI Business Insights")
    best_reg = filtered_df.groupby('region')['net_sales'].sum().idxmax()
    st.write(f"✅ **Growth Leader:** The **{best_reg}** region is currently your top performer.")
    st.write(f"⚠️ **Stockout Warning:** There are {len(filtered_df[filtered_df['inventory_on_hand']<100])} categories with low stock levels (<100 units).")

    # --- EXPORT ---
    st.download_button("📥 Download Filtered Data", filtered_df.to_csv().encode('utf-8'), "data.csv", "text/csv")
else:
    st.warning("Please ensure data files are uploaded to GitHub or use the sidebar.")
