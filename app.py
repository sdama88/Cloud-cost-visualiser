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

# Load CSV data
workloads_df = pd.read_csv("workloads.csv")
pricing_df = pd.read_csv("pricing.csv")
gpu_configs_df = pd.read_csv("gpu_configs.csv")

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

# STEP 3: GPU CONFIG SELECTION
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
default_gpu_type = workload_row["gpu_type"]
users_per_gpu = workload_row["users_per_gpu"]

auto_gpus_needed = max(1, int(num_users / users_per_gpu))

manual_mode = st.checkbox("Manual GPU selection", value=False)

if manual_mode:
    available_gpus = pricing_df["gpu_type"].unique().tolist()
    gpu_type = st.selectbox(
        "GPU Type",
        available_gpus,
        index=available_gpus.index(default_gpu_type) if default_gpu_type in available_gpus else 0,
        key="manual_gpu_type"
    )
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed)
    if num_gpus < auto_gpus_needed:
        st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")
else:
    gpu_type = default_gpu_type
    num_gpus = auto_gpus_needed

# -------------------
# DISPLAY SELECTED CONFIG
# -------------------
with st.container():
    st.markdown(
        f"""
        <div style="background-color:{REDSAND_GREY}; padding:15px; border-radius:10px;">
            <h3 style="color:{REDSAND_RED};">Selected Configuration</h3>
            <p><b>Workload:</b> {workload_name}</p>
            <p><b>Number of Users:</b> {num_users}</p>
            <p><b>GPU Type:</b> {gpu_type}</p>
            <p><b>Number of GPUs:</b> {num_gpus}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------
# CALCULATE BUTTON
# -------------------
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

        # -------------------
        # SCALING SLIDER
        # -------------------
        st.subheader("Scaling Impact")
        max_users_scale = st.slider("Max Users for Scaling Graph", min_value=100, max_value=20000, step=500, value=5000)

        scale_users = list(range(100, max_users_scale + 1, 500))
        scale_costs = []
        for u in scale_users:
            gpus_needed_scale = max(1, int(u / users_per_gpu)) if not manual_mode else num_gpus
            storage_gb_scale = gpus_needed_scale * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
            egress_gb_scale = gpus_needed_scale * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))
            gpu_cost_scale = gpu_price * 24 * 30 * gpus_needed_scale
            storage_cost_scale = storage_price * storage_gb_scale
            egress_cost_scale = egress_price * egress_gb_scale
            scale_costs.append(gpu_cost_scale + storage_cost_scale + egress_cost_scale)

        # -------------------
        # CHARTS SIDE-BY-SIDE
        # -------------------
        chart_col1, chart_col2 = st.columns(2)

        # Cost Breakdown Chart
        with chart_col1:
            fig = go.Figure()
            fig.add_trace(go.Bar(name="GPU Cost", x=["Total Cost"], y=[gpu_monthly_cost], marker_color=REDSAND_RED))
            fig.add_trace(go.Bar(name="Storage Cost", x=["Total Cost"], y=[storage_monthly_cost], marker_color="#666666"))
            fig.add_trace(go.Bar(name="Egress Cost", x=["Total Cost"], y=[egress_monthly_cost], marker_color="#999999"))
            fig.update_layout(
                barmode='stack',
                title="Cost Breakdown",
                plot_bgcolor=REDSAND_GREY,
                paper_bgcolor=REDSAND_GREY,
                font=dict(color=REDSAND_DARK),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        # Scaling Impact Chart
        with chart_col2:
            fig_scale = go.Figure()
            fig_scale.add_trace(go.Scatter(
                x=scale_users,
                y=scale_costs,
                mode="lines+markers",
                line=dict(color=REDSAND_RED, width=3),
                marker=dict(size=6),
                name="Total Cost"
            ))
            fig_scale.update_layout(
                title="Scaling Impact: Users vs Monthly Cost",
                xaxis_title="Number of Users",
                yaxis_title="Monthly Cost (USD)",
                plot_bgcolor=REDSAND_GREY,
                paper_bgcolor=REDSAND_GREY,
                font=dict(color=REDSAND_DARK),
                height=350
            )
            st.plotly_chart(fig_scale, use_container_width=True)
