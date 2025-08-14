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
# LOAD CSV DATA
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
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]

# -------------------
# STEP 2: SELECT USERS
# -------------------
st.subheader("Number of Users")
num_users = st.slider("Select number of users", min_value=10, max_value=1000, step=10, value=10)

# -------------------
# STEP 3: AUTO GPU SELECTION
# -------------------
default_gpu_type = workload_row["gpu_type"]
users_per_gpu = workload_row["users_per_gpu"]
auto_gpus_needed = max(1, int((num_users / users_per_gpu)))

# -------------------
# STEP 4: MANUAL GPU OVERRIDE
# -------------------
manual_mode = st.checkbox("Manual GPU selection", value=False)

if manual_mode:
    gpu_type = st.selectbox(
        "GPU Type",
        pricing_df["gpu_type"].unique(),
        index=pricing_df[pricing_df["gpu_type"] == default_gpu_type].index[0] if default_gpu_type in pricing_df["gpu_type"].values else 0
    )
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed)
    if num_gpus < auto_gpus_needed:
        st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")
else:
    gpu_type = default_gpu_type
    num_gpus = auto_gpus_needed

# -------------------
# STEP 5: CALCULATE COSTS
# -------------------
if gpu_type in pricing_df["gpu_type"].values:
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
    # LAYOUT WITH CONFIG SUMMARY
    # -------------------
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"<h2 style='color:{REDSAND_RED};'>💰 Total Monthly Cost: ${total_monthly_cost:,.0f}</h2>", unsafe_allow_html=True)

        # Scaling curve chart
        user_range = list(range(10, 1001, 10))
        scaling_costs = []
        for u in user_range:
            gpus_needed = max(1, int((u / users_per_gpu)))
            storage_gb_s = gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
            egress_gb_s = gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))
            cost_s = (gpu_price * 24 * 30 * gpus_needed) + (storage_price * storage_gb_s) + (egress_price * egress_gb_s)
            scaling_costs.append(cost_s)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=user_range,
            y=scaling_costs,
            mode="lines+markers",
            line_shape="spline",
            line=dict(color=REDSAND_RED, width=3),
            marker=dict(size=6)
        ))
        fig.update_layout(
            title="Scaling Impact on Cloud Costs",
            xaxis_title="Number of Users",
            yaxis_title="Monthly Cost (USD)",
            plot_bgcolor=REDSAND_GREY,
            paper_bgcolor=REDSAND_GREY,
            font=dict(color=REDSAND_DARK)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Selected Configuration")
        st.write(f"**Workload:** {workload_name}")
        st.write(f"**Number of Users:** {num_users}")
        st.write(f"**GPU Type:** {gpu_type}")
        st.write(f"**Number of GPUs:** {num_gpus}")
else:
    st.error("Selected GPU type is not found in pricing table. Please check your CSV files.")
