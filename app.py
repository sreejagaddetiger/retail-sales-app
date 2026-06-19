import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Retail Sales Intelligence", layout="wide")

st.title("📊 Retail Sales Intelligence Dashboard")
st.markdown("Upload your weekly sales and store master data to generate insights.")

# --- 1. DATA INTEGRATION ---
with st.sidebar:
    st.header("📂 Data Upload")
    sales_file = st.file_uploader("Upload Weekly Sales Data (.xlsx or .csv)", type=['xlsx', 'csv'])
    store_file = st.file_uploader("Upload Store Master Data (.xlsx or .csv)", type=['xlsx', 'csv'])

def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

if sales_file and store_file:
    # Load data
    sales_df = load_data(sales_file)
    store_df = load_data(store_file)

    # Standardize column names (case-insensitive and strip spaces)
    sales_df.columns = sales_df.columns.str.strip().str.lower()
    store_df.columns = store_df.columns.str.strip().str.lower()

    # Data Cleaning: Convert numeric columns
    numeric_cols = ['net_sales', 'gross_sales', 'sales_target', 'transactions', 'returns_amount', 'discount_amount', 'inventory_on_hand', 'stockouts']
    for col in numeric_cols:
        if col in sales_df.columns:
            sales_df[col] = pd.to_numeric(sales_df[col], errors='coerce').fillna(0)

    # Merge Data on store_id
    # We drop redundant columns like 'region', 'city', 'store_name' from sales_df if they exist in store_df
    cols_to_use = store_df.columns.difference(sales_df.columns).tolist() + ['store_id']
    df = pd.merge(sales_df, store_df[cols_to_use], on='store_id', how='left')

    # Convert Date
    df['week_start_date'] = pd.to_datetime(df['week_start_date'], errors='coerce')

    # --- 2. DYNAMIC FILTERS ---
    st.sidebar.header("🔍 Global Filters")
    
    region_list = sorted(df['region'].unique())
    selected_region = st.sidebar.multiselect("Region", region_list, default=region_list)

    city_list = sorted(df[df['region'].isin(selected_region)]['city'].unique())
    selected_city = st.sidebar.multiselect("City", city_list, default=city_list)

    format_list = sorted(df['store_format'].unique())
    selected_format = st.sidebar.multiselect("Store Format", format_list, default=format_list)

    store_list = sorted(df[df['city'].isin(selected_city)]['store_name'].unique())
    selected_store = st.sidebar.multiselect("Store Name", store_list, default=store_list)

    category_list = sorted(df['product_category'].unique())
    selected_cat = st.sidebar.multiselect("Product Category", category_list, default=category_list)

    # Apply Filters
    mask = (
        df['region'].isin(selected_region) &
        df['city'].isin(selected_city) &
        df['store_format'].isin(selected_format) &
        df['store_name'].isin(selected_store) &
        df['product_category'].isin(selected_cat)
    )
    filtered_df = df[mask]

    # --- 3. KPI CARDS ---
    total_net_sales = filtered_df['net_sales'].sum()
    total_target = filtered_df['sales_target'].sum()
    target_ach = (total_net_sales / total_target * 100) if total_target > 0 else 0
    total_trans = filtered_df['transactions'].sum()
    atv = (total_net_sales / total_trans) if total_trans > 0 else 0
    total_returns = filtered_df['returns_amount'].sum()
    return_rate = (total_returns / total_net_sales * 100) if total_net_sales > 0 else 0
    total_gross = filtered_df['gross_sales'].sum()
    discount_rate = (filtered_df['discount_amount'].sum() / total_gross * 100) if total_gross > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Net Sales", f"₹{total_net_sales:,.0f}")
    col2.metric("Target Achievement", f"{target_ach:.1f}%")
    col3.metric("Avg Trans Value (ATV)", f"₹{atv:,.2f}")
    col4.metric("Return Rate", f"{return_rate:.1f}%", delta_color="inverse")
    col5.metric("Discount Rate", f"{discount_rate:.1f}%")

    # --- 4. VISUAL ANALYTICS ---
    st.markdown("---")
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Weekly Sales Trend")
        weekly_trend = filtered_df.groupby('week_start_date')['net_sales'].sum().reset_index()
        fig_line = px.line(weekly_trend, x='week_start_date', y='net_sales', markers=True, template="plotly_white")
        st.plotly_chart(fig_line, use_container_width=True)

    with row1_col2:
        st.subheader("Sales by Region")
        reg_sales = filtered_df.groupby('region')['net_sales'].sum().reset_index()
        fig_bar = px.bar(reg_sales, x='region', y='net_sales', color='region', text_auto='.2s')
        st.plotly_chart(fig_bar, use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("Category Performance")
        cat_perf = filtered_df.groupby('product_category')['net_sales'].sum().reset_index()
        fig_tree = px.treemap(cat_perf, path=['product_category'], values='net_sales', color='net_sales', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_tree, use_container_width=True)

    with row2_col2:
        st.subheader("Top 10 Stores by Sales")
        store_lead = filtered_df.groupby('store_name')['net_sales'].sum().nlargest(10).reset_index()
        fig_lead = px.bar(store_lead, y='store_name', x='net_sales', orientation='h', color='net_sales')
        fig_lead.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_lead, use_container_width=True)

    st.subheader("⚠️ Stockout Risk Analysis")
    # Define threshold for risk
    threshold = st.slider("Define Low Stock Threshold", 0, 500, 200)
    stock_risk = filtered_df[filtered_df['inventory_on_hand'] < threshold][['store_name', 'product_category', 'inventory_on_hand', 'stockouts']]
    if not stock_risk.empty:
        st.dataframe(stock_risk.sort_values('inventory_on_hand'), use_container_width=True)
    else:
        st.success("No items currently under the low stock threshold.")

    # --- 5. AI BUSINESS INSIGHTS ---
    st.markdown("---")
    st.subheader("💡 Automated Business Insights")
    
    with st.expander("Click to view executive summary"):
        # Region Insight
        best_reg = reg_sales.loc[reg_sales['net_sales'].idxmax(), 'region']
        worst_reg = reg_sales.loc[reg_sales['net_sales'].idxmin(), 'region']
        
        # Target Insight
        target_miss = filtered_df.groupby('store_name').agg({'net_sales':'sum', 'sales_target':'sum'})
        target_miss = target_miss[target_miss['net_sales'] < target_miss['sales_target']]
        
        # Returns Insight
        high_return_cat = filtered_df.groupby('product_category')['returns_amount'].sum().idxmax()

        st.write(f"🟢 **Best Performing Region:** {best_reg}")
        st.write(f"🔴 **Region Needing Attention:** {worst_reg}")
        st.write(f"📦 **Highest Return Category:** {high_return_cat} (Action: Check quality or sizing issues)")
        if not target_miss.empty:
            st.write(f"📉 **Stores Missing Target:** {', '.join(target_miss.index[:5].tolist())}...")
        else:
            st.write("✅ All filtered stores have achieved their targets!")

    # --- 6. EXPORT ---
    st.sidebar.markdown("---")
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Download Filtered Data",
        data=csv,
        file_name='filtered_retail_data.csv',
        mime='text/csv',
    )

else:
    st.info("Please upload both Sales Data and Store Master to begin.")
    st.image("https://img.freepik.com/free-vector/data-report-manager-holding-clipboard-with-charts-data-analysis-financial-research-audit-result-report-concept-pinkish-coral-bluevector-isolated-illustration_335657-1549.jpg", width=400)
