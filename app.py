import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# -------------------
# CONFIG
# -------------------
REDSAND_RED = "#D71920"
REDSAND_GREY = "#F4F4F4"
REDSAND_DARK = "#222222"

# -------------------
# LOAD DATA
# -------------------
workloads_df = pd.read_csv("workloads.csv")
pricing_df = pd.read_csv("pricing.csv")

# -------------------
# UI SETUP
# -------------------
st.set_page_config(page_title="Cloud GPU Cost Visualiser", layout="wide")

st.markdown(f"<h1 style='color:{REDSAND_RED};'>☁️ Cloud GPU Cost Visualiser</h1>", unsafe_allow_html=True)

# -------------------
# STEP 1: SELECT WORKLOAD
# -------------------
workload_name = st.selectbox("Select Workload", workloads_df["workload_name"].unique())

# STEP 2: NUMBER OF USERS
user_range = list(range(10, 110, 10)) + list(range(200, 5001, 100))
num_users = st.select_slider("Select number of users", options=user_range, value=100)

# -------------------
# CALCULATIONS (Auto GPU Selection Only)
# -------------------
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
default_gpu_type = workload_row["gpu_type"]

users_per_gpu = workload_row["users_per_gpu"]
num_gpus = max(1, int(np.ceil(num_users / users_per_gpu)))

gpu_price = pricing_df.loc[pricing_df["gpu_type"] == default_gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == default_gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == default_gpu_type, "egress_price_per_gb"].values[0]

storage_gb_per_gpu = workload_row["storage_gb_per_gpu_base"] + (num_users * workload_row["storage_gb_per_user"])
egress_gb_per_gpu = workload_row["egress_gb_per_gpu_base"] + (num_users * workload_row["egress_gb_per_user"])

storage_gb = num_gpus * storage_gb_per_gpu
egress_gb = num_gpus * egress_gb_per_gpu

gpu_monthly_cost = gpu_price * 24 * 30 * num_gpus
storage_monthly_cost = storage_price * storage_gb
egress_monthly_cost = egress_price * egress_gb

total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

# -------------------
# DISPLAY SELECTED CONFIG
# -------------------
st.markdown(
    f"""
    <div style="background-color:{REDSAND_GREY}; padding:15px; border-radius:10px; border: 2px solid {REDSAND_RED};">
        <h3 style="color:{REDSAND_DARK};">Selected Configuration</h3>
        <p><b>Workload:</b> {workload_name}</p>
        <p><b>GPU Type:</b> {default_gpu_type}</p>
        <p><b>Number of GPUs:</b> {num_gpus}</p>
        <p><b>Users:</b> {num_users}</p>
        <h2 style="color:{REDSAND_RED};">💰 ${total_monthly_cost:,.0f} / month</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------
# COST SCALING GRAPH (Smooth Spline)
# -------------------
# Adjust range dynamically based on current selection
max_range = int(num_users * 2.5)
user_points = np.linspace(10, max_range, 100)

costs = []
for u in user_points:
    gpus_needed = max(1, int(np.ceil(u / users_per_gpu)))
    storage_gb_u = gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
    egress_gb_u = gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))
    total_cost_u = (gpu_price * 24 * 30 * gpus_needed) + (storage_price * storage_gb_u) + (egress_price * egress_gb_u)
    costs.append(total_cost_u)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=user_points,
    y=costs,
    mode='lines',
    line=dict(color=REDSAND_RED, width=3, shape='spline'),
    hovertemplate='Users: %{x:.0f}<br>Cost: $%{y:,.0f}<extra></extra>'
))

fig.update_layout(
    title="Cloud Cost Scaling with User Growth",
    xaxis_title="Number of Users",
    yaxis_title="Monthly Cost (USD)",
    plot_bgcolor=REDSAND_GREY,
    paper_bgcolor=REDSAND_GREY,
    font=dict(color=REDSAND_DARK),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)
