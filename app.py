import streamlit as st
import pandas as pd
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
# HELPER FUNCTIONS
# -------------------
def load_csv_clean(path):
    """Load CSV and normalize headers."""
    df = pd.read_csv(path)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace('"', '')
        .str.replace("'", '')
    )
    return df

# -------------------
# LOAD DATA
# -------------------
workloads_df = load_csv_clean("workloads.csv")
pricing_df = load_csv_clean("pricing.csv")
gpu_configs_df = load_csv_clean("gpu_configs.csv")

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
default_gpu_type = workload_row["gpu_type"]
users_per_gpu = workload_row["users_per_gpu"]

auto_gpus_needed = max(1, int((num_users / users_per_gpu)))

# STEP 4: GPU SELECTION (Auto + Manual)
st.subheader("GPU Selection")

# Auto calculate required GPUs
users_per_gpu = workload_row["users_per_gpu"]
auto_gpus_needed = max(1, int((num_users / users_per_gpu)))

default_gpu_type = workload_row["gpu_type"]

manual_mode = st.checkbox("Manual GPU selection", value=False)

if manual_mode:
    gpu_type = st.selectbox(
        "GPU Type",
        pricing_df["gpu_type"].unique(),
        index=pricing_df[pricing_df["gpu_type"] == default_gpu_type].index[0]
        if default_gpu_type in pricing_df["gpu_type"].values else 0,
        key="manual_gpu_type"
    )
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed, key="manual_gpu_count")
    if num_gpus < auto_gpus_needed:
        st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")
    selection_source = "Manual"
else:
    gpu_type = default_gpu_type
    num_gpus = auto_gpus_needed
    selection_source = "Automatic"

# Display selected GPU config
st.markdown(
    f"<div style='background-color:#F4F4F4;padding:10px;border-radius:8px;'>"
    f"<strong>Selected GPU Configuration ({selection_source}):</strong> "
    f"{num_gpus} × {gpu_type}</div>",
    unsafe_allow_html=True
)

# STEP 5: CALCULATE COSTS
gpu_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "egress_price_per_gb"].values[0]

storage_gb_per_gpu = workload_row["storage_gb_per_gpu_base"] + (num_users * workload_row["storage_gb_per_user"])
egress_gb_per_gpu = workload_row["egress_gb_per_gpu_base"] + (num_users * workload_row["egress_gb_per_user"])

storage_gb = num_gpus * storage_gb_per_gpu
egress_gb = num_gpus * egress_gb_per_gpu

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
fig.add_trace(go.Bar(name="GPU Cost", x=["Total Cost"], y=[gpu_monthly_cost], marker_color=REDSAND_RED))
fig.add_trace(go.Bar(name="Storage Cost", x=["Total Cost"], y=[storage_monthly_cost], marker_color="#666666"))
fig.add_trace(go.Bar(name="Egress Cost", x=["Total Cost"], y=[egress_monthly_cost], marker_color="#999999"))
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
    * Actual cloud pricing may vary.
    </small>
    """,
    unsafe_allow_html=True
)
