import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO

# -------------------
# CONFIG
# -------------------
WORKLOADS_FILE = "workloads.csv"
PRICING_FILE = "pricing.csv"
GPU_CONFIGS_FILE = "gpu_configs.csv"

# Redsand brand colors
REDSAND_RED = "#D71920"
REDSAND_GREY = "#F4F4F4"
REDSAND_DARK = "#222222"

# -------------------
# LOAD DATA
# -------------------
@st.cache_data
def load_csv(filename):
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    return df

workloads_df = load_csv(WORKLOADS_FILE)
pricing_df = load_csv(PRICING_FILE)
gpu_configs_df = load_csv(GPU_CONFIGS_FILE)

# -------------------
# PAGE SETUP
# -------------------
st.set_page_config(page_title="Cloud GPU Cost Visualiser", page_icon="☁️", layout="wide")

# Logo
try:
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
except FileNotFoundError:
    st.markdown(f"<h1 style='color:{REDSAND_RED};'>☁️ Cloud GPU Cost Visualiser</h1>", unsafe_allow_html=True)

# -------------------
# STEP 1: SELECT WORKLOAD
# -------------------
st.subheader("Select Workload")
workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())

# STEP 2: NUMBER OF USERS
st.subheader("Number of Users")
user_range = list(range(10, 110, 10)) + list(range(200, 10001, 100))
num_users = st.select_slider("Select number of users", options=user_range)

# STEP 3: AUTO GPU SELECTION
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]

users_per_gpu = workload_row["users_per_gpu"]
gpu_type_auto = workload_row["gpu_type"]

auto_gpus_needed = max(1, int((num_users / users_per_gpu)))

# STEP 4: MANUAL OVERRIDE
st.subheader("GPU Configuration")
st.write(f"**Auto-selected GPU Type:** {gpu_type_auto} ({auto_gpus_needed} GPUs recommended)")

manual_mode = st.checkbox("Manual GPU selection", value=False)

if manual_mode:
    gpu_type = st.selectbox("GPU Type", pricing_df["gpu_type"].unique(), 
                            index=pricing_df[pricing_df["gpu_type"] == gpu_type_auto].index[0] 
                            if gpu_type_auto in pricing_df["gpu_type"].values else 0)
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed)
    if num_gpus < auto_gpus_needed:
        st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")
else:
    gpu_type = gpu_type_auto
    num_gpus = auto_gpus_needed

# -------------------
# STEP 5: COST CALCULATION
# -------------------
gpu_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "egress_price_per_gb"].values[0]

storage_gb = (workload_row["storage_gb_per_gpu_base"] + (num_users * workload_row["storage_gb_per_user"])) * num_gpus
egress_gb = (workload_row["egress_gb_per_gpu_base"] + (num_users * workload_row["egress_gb_per_user"])) * num_gpus

gpu_monthly_cost = gpu_price * 24 * 30 * num_gpus
storage_monthly_cost = storage_price * storage_gb
egress_monthly_cost = egress_price * egress_gb

total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

# -------------------
# DISPLAY COSTS
# -------------------
st.markdown(f"<h2 style='color:{REDSAND_RED};'>💰 Total Monthly Cost: ${total_monthly_cost:,.0f}</h2>", unsafe_allow_html=True)

# Cost breakdown chart
fig = go.Figure()
fig.add_trace(go.Bar(
    name="GPU Cost",
    x=["Total Cost"],
    y=[gpu_monthly_cost],
    marker_color=REDSAND_RED
))
fig.add_trace(go.Bar(
    name="Storage Cost",
    x=["Total Cost"],
    y=[storage_monthly_cost],
    marker_color="#666666"
))
fig.add_trace(go.Bar(
    name="Egress Cost",
    x=["Total Cost"],
    y=[egress_monthly_cost],
    marker_color="#999999"
))
fig.update_layout(
    barmode='stack',
    title="Cost Breakdown",
    plot_bgcolor=REDSAND_GREY,
    paper_bgcolor=REDSAND_GREY,
    font=dict(color=REDSAND_DARK)
)
st.plotly_chart(fig, use_container_width=True)

# -------------------
# FOOTNOTES
# -------------------
st.markdown(
    """
    <hr>
    <small>
    * Estimates based on selected workload, GPU type, and user count.  
    * Costs include GPU compute, storage, and egress.  
    * Update CSV files to adjust workloads, pricing, or GPU configs.
    </small>
    """,
    unsafe_allow_html=True
)
