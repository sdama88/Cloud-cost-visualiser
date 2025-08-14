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
# LOAD CSV FILES
# -------------------
workloads_df = pd.read_csv("workloads.csv")
pricing_df = pd.read_csv("pricing.csv")
gpu_configs_df = pd.read_csv("gpu_configs.csv")

# Strip column names
workloads_df.columns = workloads_df.columns.str.strip()
pricing_df.columns = pricing_df.columns.str.strip()
gpu_configs_df.columns = gpu_configs_df.columns.str.strip()

# -------------------
# STREAMLIT PAGE CONFIG
# -------------------
st.set_page_config(page_title="Cloud GPU Cost Visualiser", page_icon="☁️", layout="wide")

# -------------------
# LOGO + TITLE
# -------------------
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
# MAIN LAYOUT
# -------------------
left_col, right_col = st.columns([2, 1])

with left_col:
    # STEP 1: SELECT WORKLOAD
    st.subheader("Select Workload")
    workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())
    workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]

    # STEP 2: NUMBER OF USERS
    st.subheader("Number of Users")
    user_range = list(range(10, 110, 10)) + list(range(200, 10001, 100))
    num_users = st.select_slider("Select number of users", options=user_range)

    # STEP 3: AUTO GPU CALC
    default_gpu_type = workload_row["gpu_type"]
    users_per_gpu = workload_row["users_per_gpu"]
    auto_gpus_needed = max(1, int(num_users / users_per_gpu))

    # STEP 4: MANUAL GPU SELECTION
    manual_mode = st.checkbox("Manual GPU selection", value=False)
    gpu_type = default_gpu_type
    num_gpus = auto_gpus_needed

    if manual_mode:
        gpu_type_options = pricing_df["gpu_type"].unique()
        if default_gpu_type in gpu_type_options:
            default_index = list(gpu_type_options).index(default_gpu_type)
        else:
            default_index = 0

        gpu_type = st.selectbox(
            "GPU Type",
            options=gpu_type_options,
            index=default_index,
            key="manual_gpu_type"
        )
        num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed)
        if num_gpus < auto_gpus_needed:
            st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")

with right_col:
    st.markdown(
        f"""
        <div style="background-color:{REDSAND_GREY}; padding: 20px; border-radius: 12px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
            <h3 style="color:{REDSAND_RED};">📋 Selected Configuration</h3>
            <p><strong>Workload:</strong> {workload_name}</p>
            <p><strong>Users:</strong> {num_users}</p>
            <p><strong>GPU Type:</strong> {gpu_type}</p>
            <p><strong>Number of GPUs:</strong> {num_gpus}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------
# CALCULATION ON BUTTON CLICK
# -------------------
st.markdown("---")
if st.button("Calculate Costs"):
    gpu_row = pricing_df[pricing_df["gpu_type"] == gpu_type]
    if gpu_row.empty:
        st.error("❌ Selected GPU type not found in pricing data.")
    else:
        gpu_price = gpu_row["gpu_hourly_usd"].values[0]
        storage_price = gpu_row["storage_price_per_gb_month"].values[0]
        egress_price = gpu_row["egress_price_per_gb"].values[0]

        storage_gb_per_gpu = workload_row["storage_gb_per_gpu_base"] + (num_users * workload_row["storage_gb_per_user"])
        egress_gb_per_gpu = workload_row["egress_gb_per_gpu_base"] + (num_users * workload_row["egress_gb_per_user"])

        storage_gb = num_gpus * storage_gb_per_gpu
        egress_gb = num_gpus * egress_gb_per_gpu

        gpu_monthly_cost = gpu_price * 24 * 30 * num_gpus
        storage_monthly_cost = storage_price * storage_gb
        egress_monthly_cost = egress_price * egress_gb
        total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

        st.markdown(
            f"<h2 style='color:{REDSAND_RED};'>💰 Total Monthly Cost: ${total_monthly_cost:,.0f}</h2>",
            unsafe_allow_html=True
        )

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
