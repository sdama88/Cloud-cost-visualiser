import streamlit as st
import pandas as pd
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
@st.cache_data
def load_csv(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    return df

workloads_df = load_csv("workloads.csv")
pricing_df = load_csv("pricing.csv")
upgrade_rules_df = load_csv("gpu_upgrade_rules.csv")

# -------------------
# PAGE CONFIG
# -------------------
st.set_page_config(page_title="Cloud GPU Cost Visualiser", page_icon="☁️", layout="wide")

st.markdown(
    f"""
    <h1 style="color:{REDSAND_RED}; margin: 0;">☁️ Cloud GPU Cost Visualiser</h1>
    """,
    unsafe_allow_html=True
)

# -------------------
# WORKLOAD SELECTION
# -------------------
st.subheader("Select Workload")
workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())

# Number of Users
st.subheader("Number of Concurrent Human Users")
user_range = list(range(10, 1001, 10))
num_users = st.slider("Select number of users", min_value=10, max_value=1000, step=10, value=10)

# -------------------
# AUTO GPU SELECTION WITH SILENT UPGRADE
# -------------------
# Start with base workload config
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
gpu_type = workload_row["gpu_type"]

# Check for silent upgrade first
upgrade_row = upgrade_rules_df[
    (upgrade_rules_df["current_gpu"] == gpu_type) &
    (num_users >= upgrade_rules_df["user_threshold"])
]
if not upgrade_row.empty:
    gpu_type = upgrade_row.iloc[0]["new_gpu"]

# Get the correct users_per_gpu for the (possibly upgraded) GPU
gpu_users_per_gpu = workloads_df.loc[workloads_df["gpu_type"] == gpu_type, "users_per_gpu"].values[0]

# Calculate GPUs needed based on upgraded GPU type
gpus_needed = max(1, int((num_users / gpu_users_per_gpu)))

# Apply hyperscaler-friendly rounding
if gpus_needed <= 4:
    gpus_needed = 4
elif gpus_needed <= 8:
    gpus_needed = 8
elif gpus_needed <= 16:
    gpus_needed = 16

auto_gpus_needed = gpus_needed

# -------------------
# COST CALCULATIONS
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
# DISPLAY CONFIG & COST
# -------------------
col1, col2 = st.columns([1, 1])
with col1:
    st.markdown(f"""
    <div style="border:2px solid {REDSAND_RED}; border-radius:10px; padding:15px; background-color:white;">
    <h3 style="color:{REDSAND_RED};">Selected Configuration</h3>
    <p><b>Workload:</b> {workload_name}</p>
    <p><b>Concurrent Users:</b> {num_users}</p>
    <p><b>GPU Type:</b> {gpu_type}</p>
    <p><b>Number of GPUs:</b> {auto_gpus_needed}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.metric("💰 Total Monthly Cost", f"${total_monthly_cost:,.0f}")

# -------------------
# COST SCALING GRAPH (fixed)
# -------------------
user_values = list(range(10, 1001, 10))
cost_values = []

for u in user_values:
    # Start with base GPU type for the workload
    gpu_sel = workload_row["gpu_type"]

    # Check for silent upgrade
    upgrade_check = upgrade_rules_df[
        (upgrade_rules_df["current_gpu"] == gpu_sel) &
        (u >= upgrade_rules_df["user_threshold"])
    ]
    if not upgrade_check.empty:
        gpu_sel = upgrade_check.iloc[0]["new_gpu"]

    # Get users_per_gpu for selected (possibly upgraded) GPU
    gpu_users_per_gpu = workloads_df.loc[workloads_df["gpu_type"] == gpu_sel, "users_per_gpu"].values[0]

    # Calculate GPUs needed
    gpus_needed = max(1, int((u / gpu_users_per_gpu)))

    # Apply hyperscaler-friendly rounding
    if gpus_needed <= 4:
        gpus_needed = 4
    elif gpus_needed <= 8:
        gpus_needed = 8
    elif gpus_needed <= 16:
        gpus_needed = 16

    # Pricing and usage calculations
    g_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_sel, "gpu_hourly_usd"].values[0]
    s_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_sel, "storage_price_per_gb_month"].values[0]
    e_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_sel, "egress_price_per_gb"].values[0]

    s_gb = gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
    e_gb = gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))

    total_cost = (g_price * 24 * 30 * gpus_needed) + (s_price * s_gb) + (e_price * e_gb)
    cost_values.append(total_cost)
