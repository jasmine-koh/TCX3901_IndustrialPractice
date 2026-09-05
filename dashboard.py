import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Olist Delivery Performance Dashboard",
    layout="wide"
)

st.title("Olist Delivery Performance Dashboard")

st.write(
    "Interactive dashboard for exploring delivery performance "
    "in the Olist Brazilian E-Commerce datatset."
)



# Load Dashboard Data
df = pd.read_csv("olist_delivery_dashboard.csv", parse_dates=["order_purchase_timestamp"])


# Filters
# Dashboard Filters
filter_col1, filter_col2 = st.columns(2)

# Customer State Filter
# sort the list of unique/no null/na customer state
# add 'All' to the list
state_options = ["All"] + sorted(df["customer_state"].dropna().unique().tolist())

# create selector
with filter_col1:
    selected_state = st.selectbox("Customer State", state_options)

# Purchase Date Filter
min_date = df['order_purchase_timestamp'].min().date()
max_date = df['order_purchase_timestamp'].max().date()

with filter_col2:
    start_date = st.date_input(
        "Start Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )

    end_date = st.date_input(
        "End Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )

# Apply Filters
filtered_df = df.copy()

# state filter
if selected_state != "All":
    filtered_df = filtered_df[filtered_df["customer_state"] == selected_state]

# date range filter
if start_date <= end_date:
    filtered_df = filtered_df[
        (filtered_df["order_purchase_timestamp"].dt.date >= start_date)
        & (filtered_df["order_purchase_timestamp"].dt.date <= end_date)
    ]
else:
    st.warning("Start Date must be before End Date.")


# Calculate Metrics
total_orders = len(filtered_df)
median_delivery = filtered_df["actual_delivery_days"].median()
late_rate = filtered_df["is_late"].mean() * 100

# Display Metrics
col1, col2, col3 = st.columns(3)

col1.metric("Total Orders", f"{total_orders:,}")
col2.metric("Median Delivery Times", f"{median_delivery:.2f} days")
col3.metric("Late Delivery Rate", f"{late_rate:.2f}%")


# Charts
# Actual vs Estimate Delivery Lead Times
st.subheader("Actual vs Estimated Delivery Lead Time")

# Calculate fixed 99th-percentile cut-offs from full dataset
actual_99 = df["actual_delivery_days"].quantile(0.99)
estimated_99 = df["estimated_delivery_days"].quantile(0.99)

# Prepare actual delivery times up to the 99th percentile
actual_plot = filtered_df.loc[
    filtered_df["actual_delivery_days"] <= actual_99,
    ["actual_delivery_days"]
].rename(
    columns={"actual_delivery_days": "Delivery Days"}
)

actual_plot["Delivery Type"] = "Actual"

# Prepare estimated delivery times up to the 99th percentile
estimated_plot = filtered_df.loc[
    filtered_df["estimated_delivery_days"] <= actual_99,
    ["estimated_delivery_days"]
].rename(
    columns={"estimated_delivery_days": "Delivery Days"}
)

estimated_plot["Delivery Type"] = "Estimated"

# Combine both for plotting
lead_time_long = pd.concat([actual_plot, estimated_plot], ignore_index=True)

fig_lead_time = px.histogram(
    lead_time_long,
    x="Delivery Days",
    color="Delivery Type",
    barmode="overlay",
    nbins=50,
    opacity=0.6
)

fig_lead_time.update_layout(
    legend_title_text="Delivery Type",
    xaxis_title="Delivery Lead Time (Days)",
    yaxis_title="Number of Orders")

st.plotly_chart(fig_lead_time, width='stretch')

# Late vs On Time Delivery Breakdown
st.subheader("Late vs On Time Delivery Breakdown")

delivery_status = (
    filtered_df["is_late"]
    .value_counts()
    .rename(index={0: "On Time", 1: "Late"})
    .reset_index()
)

delivery_status.columns = ["Delivery Status", "Number of Orders"]

delivery_status["Percentage"] = (
    delivery_status["Number of Orders"] / delivery_status["Number of Orders"].sum() * 100
)

delivery_status["Label"] = (
    delivery_status["Number of Orders"].map("{:,}".format)
    + " ("
    + delivery_status["Percentage"].map("{:.2f}%".format)
    + ")"
)

fig_delivery_status = px.bar(
    delivery_status,
    x="Delivery Status",
    y="Number of Orders",
    text="Label"
)

fig_delivery_status.update_layout(
    xaxis_title="Delivery Status",
    yaxis_title="Number of Orders",
    showlegend=False
)

st.plotly_chart(fig_delivery_status, width="stretch")

# Seller Composition
st.subheader("Seller Composition")

multi_seller_pct = ((filtered_df["seller_count"] > 1).mean() * 100)
multi_seller_state_pct = ((filtered_df["seller_state_count"] > 1).mean() * 100)

seller_composition = pd.DataFrame({
    "Seller Composition": ["Multiple Sellers", "Multi Seller States"],
    "Percentage of Orders": [multi_seller_pct, multi_seller_state_pct]
})

seller_composition["Label"] = (
    seller_composition["Percentage of Orders"].map("{:.2f}%".format)
)

fig_seller_composition = px.bar(
    seller_composition,
    x="Seller Composition",
    y="Percentage of Orders",
    text="Label"
)

fig_seller_composition.update_layout(
    xaxis_title="Seller Composition",
    yaxis_title="Percentage of Orders (%)",
    showlegend=False
)

st.plotly_chart(fig_seller_composition, width="stretch")

# Seller Composition and Delivery Performance
st.subheader("Delivery Performance by Seller Composition")

# Create seller composition groups
seller_performance_df = filtered_df.copy()

seller_performance_df["Seller Group"] = seller_performance_df["seller_count"].apply(
    lambda x: "Multiple Sellers" if x > 1 else "Single Seller"
)

seller_performance_df["Seller State Group"] = seller_performance_df["seller_state_count"].apply(
    lambda x: "Multiple Seller States" if x > 1 else "Single Seller State"
)

# Performance by Number of Sellers
seller_group_table = (
    seller_performance_df.groupby("Seller Group").agg(
        Order=("order_id", "count"),
        Median_Delivery_Days=("actual_delivery_days", "median"),
        Mean_Delivery_Days=("actual_delivery_days", "mean"),
        Late_Rate=("is_late", "mean")
    ).reset_index()
)

seller_group_table["Late_Rate"] *= 100

# Performance by Number of Seller States
seller_state_table = (
    seller_performance_df.groupby("Seller State Group").agg(
        Order=("order_id", "count"),
        Median_Delivery_Days=("actual_delivery_days", "median"),
        Mean_Delivery_Days=("actual_delivery_days", "mean"),
        Late_Rate=("is_late", "mean")
    ).reset_index()
)

seller_state_table["Late_Rate"] *= 100

# Display performance in tabular format
table_col1, table_col2 = st.columns(2)

with table_col1:
    st.write("**Nmber of Sellers**")
    st.dataframe(
        seller_group_table,
        width='stretch',
        hide_index=True,
        column_config={
            "Seller Group": "Seller Group",
            "Orders": st.column_config.NumberColumn("Orders", format="%d"),
            "Median_Delivery_Days": st.column_config.NumberColumn("Median Delivery Days", format="%.2f"),
            "Mean_Delivery_Days": st.column_config.NumberColumn("Mean Delivery Days", format="%.2f"),
            "Late_Rate": st.column_config.NumberColumn("Late Rate", format="%.2f%%")
        }
    )

with table_col2:
    st.write("**Nmber of Sellers States**")
    st.dataframe(
        seller_state_table,
        width='stretch',
        hide_index=True,
        column_config={
            "Seller State Group": "Seller State Group",
            "Orders": st.column_config.NumberColumn("Orders", format="%d"),
            "Median_Delivery_Days": st.column_config.NumberColumn("Median Delivery Days", format="%.2f"),
            "Mean_Delivery_Days": st.column_config.NumberColumn("Mean Delivery Days", format="%.2f"),
            "Late_Rate": st.column_config.NumberColumn("Late Rate", format="%.2f%%")
        }
    )