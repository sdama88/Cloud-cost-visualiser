import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO
import numpy as np

# -------------------
# CONFIG
# -------------------
REDSAND_RED = "#D71920"
REDSAND_GREY = "#F4F4F4"
REDSAND_DARK = "#222222"

# Load CSV files
workloads_df = pd.read_csv("workloads.csv")
pricing_df = pd.read_csv("pricing.csv")

# -------------------
# UI SETUP
# -------------------
st.set_page_config(page_title="Cloud GPU Cost Visualiser", page_icon="☁️", layout="wide")

# Logo
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <a href="https://redsand.ai" target="_blank">
            <img src="data:image/png;base64,{img_str}" width="120">
        </a>
        <h1 style="color:{REDSAND_RED}; margin: 0;">☁️ Cloud GPU Cost Visualiser</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------
# WORKLOAD SELECTION
# -------------------
st.subheader("Select Workload")
workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())

# Slider for number of users (start at 10)
st.subheader("Number of Users")
user_range = list(range(10, 10001, 10))
num_users = st.select_slider("Select number of users", options=user_range, value=10)

# -------------------
# CALCULATE GPU CONFIG
# -------------------
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
default_gpu_type = workload_row["gpu_type"]
users_per_gpu = workload_row["users_per_gpu"]

auto_gpus_needed = max(1, int((num_users / users_per_gpu)))

gpu_price = pricing_df.loc[pricing_df["gpu_type"] == default_gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == default_gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == default_gpu_type, "egress_price_per_gb"].values[0]

storage_gb_per_gpu = workload_row["storage_gb_per_gpu_base"] + (num_users * workload_row["storage_gb_per_user"])
egress_gb_per_gpu = workload_row["egress_gb_per_gpu_base"] + (num_users * workload_row["egress_gb_per_user"])

storage_gb = auto_gpus_needed * storage_gb_per_gpu
egress_gb = auto_gpus_needed * egress_gb_per_gpu

gpu_monthly_cost = gpu_price * 24 * 30 * auto_gpus_needed
storage_monthly_cost = storage_price * storage_gb
egress_monthly_cost = egress_price * egress_gb

total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

# -------------------
# DISPLAY CONFIGURATION
# -------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown(f"""
    <div style="background-color:{REDSAND_GREY}; padding:15px; border-radius:10px;">
        <h3 style="color:{REDSAND_RED};">Selected Configuration</h3>
        <p><b>Workload:</b> {workload_name}</p>
        <p><b>GPU Type:</b> {default_gpu_type}</p>
        <p><b>Number of GPUs:</b> {auto_gpus_needed}</p>
        <p><b>Users:</b> {num_users}</p>
        <h2 style="color:{REDSAND_RED};">💰 ${total_monthly_cost:,.0f} / month</h2>
    </div>
    """, unsafe_allow_html=True)

# -------------------
# COST VS USERS CURVE
# -------------------
# Create a smooth curve for cost scaling
user_values = np.linspace(10, 10000, 100)
cost_values = []
for u in user_values:
    gpus_needed = max(1, int((u / users_per_gpu)))
    s_gb = gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
    e_gb = gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))
    gpu_cost = gpu_price * 24 * 30 * gpus_needed
    storage_cost = storage_price * s_gb
    egress_cost = egress_price * e_gb
    total_cost = gpu_cost + storage_cost + egress_cost
    cost_values.append(total_cost)

with col2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=user_values,
        y=cost_values,
        mode='lines',
        line=dict(color=REDSAND_RED, width=3),
        name="Cost vs Users"
    ))
    fig.update_layout(
        title="Cloud Cost Scaling",
        xaxis_title="Number of Users",
        yaxis_title="Monthly Cost (USD)",
        plot_bgcolor=REDSAND_GREY,
        paper_bgcolor=REDSAND_GREY,
        font=dict(color=REDSAND_DARK)
    )
    st.plotly_chart(fig, use_container_width=True)
