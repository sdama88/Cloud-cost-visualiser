import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO

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
gpu_configs_df = pd.read_csv("gpu_configs.csv")

# -------------------
# STREAMLIT PAGE CONFIG
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
# STEP 1: SELECT WORKLOAD
# -------------------
st.subheader("Select Workload")
workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())

# STEP 2: NUMBER OF USERS
st.subheader("Number of Users")
user_range = list(range(10, 110, 10)) + list(range(200, 10001, 100))
num_users = st.select_slider("Select number of users", options=user_range)

# Get workload details
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
gpu_type = workload_row["gpu_type"]
users_per_gpu = workload_row["users_per_gpu"]

# -------------------
# AUTO GPU COUNT ROUNDING
# -------------------
def round_to_4_or_8(x):
    if x <= 4:
        return 4
    elif x <= 8:
        return 8
    else:
        remainder = x % 8
        return x if remainder == 0 else x + (8 - remainder)

auto_gpus_needed = max(1, math.ceil(num_users / users_per_gpu))
auto_gpus_needed = round_to_4_or_8(auto_gpus_needed)

# -------------------
# DISPLAY CONFIG SUMMARY
# -------------------
with st.container():
    st.markdown(
        f"""
        <div style="background-color: {REDSAND_GREY}; padding: 15px; border-radius: 10px; border: 2px solid {REDSAND_RED};">
            <h3 style="color:{REDSAND_DARK}; margin-top: 0;">📊 Selected Configuration</h3>
            <p><strong>Workload:</strong> {workload_name}</p>
            <p><strong>Concurrent Users:</strong> {num_users}</p>
            <p><strong>GPU Type:</strong> {gpu_type}</p>
            <p><strong>Number of GPUs:</strong> {auto_gpus_needed}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------
# CALCULATE COSTS
# -------------------
gpu_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "egress_price_per_gb"].values[0]

storage_gb_per_gpu = workload_row["storage_gb_per_gpu_base"] + (num_users * workload_row["storage_gb_per_user"])
egress_gb_per_gpu = workload_row["egress_gb_per_gpu_base"] + (num_users * workload_row["egress_gb_per_user"])

storage_gb = auto_gpus_needed * storage_gb_per_gpu
egress_gb = auto_gpus_needed * egress_gb_per_gpu

gpu_monthly_cost = gpu_price * 24 * 30 * auto_gpus_needed
storage_monthly_cost = storage_price * storage_gb
egress_monthly_cost = egress_price * egress_gb

total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

# -------------------
# TOTAL COST DISPLAY
# -------------------
st.markdown(f"<h2 style='color:{REDSAND_RED};'>💰 Total Monthly Cost: ${total_monthly_cost:,.0f}</h2>", unsafe_allow_html=True)

# -------------------
# COST VS USERS CURVE
# -------------------
user_values = list(range(10, 1001, 10))
cost_values = []
for u in user_values:
    gpus_needed = round_to_4_or_8(max(1, math.ceil(u / users_per_gpu)))
    storage_gb = gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
    egress_gb = gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))
    gpu_cost = gpu_price * 24 * 30 * gpus_needed
    storage_cost = storage_price * storage_gb
    egress_cost = egress_price * egress_gb
    total_cost = gpu_cost + storage_cost + egress_cost
    cost_values.append(total_cost)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=user_values,
    y=cost_values,
    mode='lines',
    line=dict(color=REDSAND_RED, width=3),
    name='Total Cost'
))
fig.update_layout(
    title="Scaling Cost with Users",
    xaxis_title="Number of Concurrent Users",
    yaxis_title="Monthly Cost (USD)",
    plot_bgcolor=REDSAND_GREY,
    paper_bgcolor=REDSAND_GREY,
    font=dict(color=REDSAND_DARK)
)
st.plotly_chart(fig, use_container_width=True)
