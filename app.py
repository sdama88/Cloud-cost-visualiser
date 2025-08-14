import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO

# -------------------
# CONFIG
# -------------------
WORKLOADS_CSV = "workloads.csv"
PRICING_CSV = "pricing.csv"
REDSAND_RED = "#D71920"
REDSAND_GREY = "#F4F4F4"
REDSAND_DARK = "#222222"

# -------------------
# LOAD CSV DATA
# -------------------
workloads_df = pd.read_csv(WORKLOADS_CSV)
pricing_df = pd.read_csv(PRICING_CSV)

# Strip spaces from column names
workloads_df.columns = workloads_df.columns.str.strip().str.lower()
pricing_df.columns = pricing_df.columns.str.strip().str.lower()

# -------------------
# UI SETUP
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
except:
    st.title("☁️ Cloud GPU Cost Visualiser")

# -------------------
# STEP 1: SELECT WORKLOAD
# -------------------
st.subheader("Select Workload")
workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())

# STEP 2: NUMBER OF USERS SLIDER
st.subheader("Number of Users")
user_range = list(range(10, 110, 10)) + list(range(200, 10001, 100))
num_users = st.select_slider("Select number of users", options=user_range)

# Get workload row
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
default_gpu_type = workload_row["gpu_type"]
users_per_gpu = workload_row["users_per_gpu"]

# Auto GPUs
auto_gpus_needed = max(1, int((num_users / users_per_gpu)))

# -------------------
# STEP 3: MANUAL OVERRIDE
# -------------------
manual_mode = st.checkbox("Manual GPU selection", value=False)

gpu_type = None
num_gpus = None

if manual_mode:
    gpu_type_options = pricing_df["gpu_type"].unique()
    if default_gpu_type in gpu_type_options:
        default_index = list(gpu_type_options).index(default_gpu_type)
    else:
        default_index = 0
    gpu_type = st.selectbox("GPU Type", gpu_type_options, index=default_index)
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed)
    if num_gpus < auto_gpus_needed:
        st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")
else:
    gpu_type = default_gpu_type
    num_gpus = auto_gpus_needed

# -------------------
# SHOW CONFIG SUMMARY
# -------------------
st.markdown("### Selected Configuration")
st.info(f"""
**Workload:** {workload_name}  
**Number of Users:** {num_users}  
**GPU Type:** {gpu_type if gpu_type else 'Not selected'}  
**Number of GPUs:** {num_gpus if num_gpus else 'Not selected'}  
""")

# -------------------
# STEP 4: COST CALCULATION & GRAPH
# -------------------
if gpu_type and num_gpus:
    # Get pricing
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

    st.markdown(f"<h2 style='color:{REDSAND_RED};'>💰 Total Monthly Cost: ${total_monthly_cost:,.0f}</h2>", unsafe_allow_html=True)

    # Create scaling curve
    scaling_users = list(range(10, 2001, 50))
    scaling_costs = []
    for u in scaling_users:
        gpus_needed = max(1, int(u / users_per_gpu))
        s_gb = gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"]))
        e_gb = gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"]))
        gpu_cost = gpu_price * 24 * 30 * gpus_needed
        storage_cost = storage_price * s_gb
        egress_cost = egress_price * e_gb
        scaling_costs.append(gpu_cost + storage_cost + egress_cost)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scaling_users,
        y=scaling_costs,
        mode='lines+markers',
        line_shape='spline',
        name="Cost vs Users",
        line=dict(color=REDSAND_RED, width=3)
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
else:
    st.warning("⚠️ Please select a valid GPU type to see calculations.")
