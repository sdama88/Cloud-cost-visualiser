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
@st.cache_data
def load_csv(filename):
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    return df

workloads_df = load_csv("workloads.csv")
pricing_df = load_csv("pricing.csv")
gpu_configs_df = load_csv("gpu_configs.csv")

# -------------------
# PAGE SETUP
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
# INPUTS
# -------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Select Workload")
    workload_name = st.selectbox("Workload", workloads_df["workload_name"].unique())

    st.subheader("Number of Users")
    user_range = list(range(10, 110, 10)) + list(range(200, 10001, 100))
    num_users = st.select_slider("Select number of users", options=user_range)

    workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]
    default_gpu_type = workload_row["gpu_type"]

    users_per_gpu = workload_row["users_per_gpu"]
    auto_gpus_needed = max(1, int(num_users / users_per_gpu))

    manual_mode = st.checkbox("Manual GPU selection", value=False)

    if manual_mode:
        if default_gpu_type in pricing_df["gpu_type"].values:
            default_index = pricing_df[pricing_df["gpu_type"] == default_gpu_type].index[0]
        else:
            default_index = 0
        gpu_type = st.selectbox(
            "GPU Type",
            pricing_df["gpu_type"].unique(),
            index=default_index
        )
        num_gpus = st.number_input("Number of GPUs", min_value=1, value=auto_gpus_needed)
        if num_gpus < auto_gpus_needed:
            st.warning(f"⚠️ Selected GPUs may be underpowered. Recommended: {auto_gpus_needed} GPUs")
    else:
        gpu_type = default_gpu_type
        num_gpus = auto_gpus_needed

with col2:
    st.subheader("Selected Configuration")
    st.markdown(f"""
    **Workload:** {workload_name}  
    **Users:** {num_users}  
    **GPU Type:** {gpu_type}  
    **Number of GPUs:** {num_gpus}  
    """)

# -------------------
# CALCULATIONS & DISPLAY
# -------------------
if gpu_type and num_gpus > 0:
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

    # Display total cost
    st.markdown(f"<h2 style='color:{REDSAND_RED};'>💰 Total Monthly Cost: ${total_monthly_cost:,.0f}</h2>", unsafe_allow_html=True)

    # Layout for charts
    chart_col1, chart_col2 = st.columns([1, 1])

    with chart_col1:
        # Cost breakdown stacked bar
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

    with chart_col2:
        # Scaling curve
        scale_users = list(range(10, 10001, 100))
        scale_costs = []
        for u in scale_users:
            gpus_needed = max(1, int(u / users_per_gpu))
            gpu_c = gpu_price * 24 * 30 * gpus_needed
            storage_c = storage_price * (gpus_needed * (workload_row["storage_gb_per_gpu_base"] + (u * workload_row["storage_gb_per_user"])))
            egress_c = egress_price * (gpus_needed * (workload_row["egress_gb_per_gpu_base"] + (u * workload_row["egress_gb_per_user"])))
            scale_costs.append(gpu_c + storage_c + egress_c)

        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=scale_users, y=scale_costs,
            mode='lines',
            line=dict(shape='spline', color=REDSAND_RED, width=3),
            fill='tozeroy',
            name='Scaling Cost'
        ))
        fig_curve.add_trace(go.Scatter(
            x=[num_users], y=[total_monthly_cost],
            mode='markers+text',
            marker=dict(size=12, color=REDSAND_DARK),
            text=["Current"],
            textposition="top center",
            name="Selected"
        ))
        fig_curve.update_layout(
            title="Scaling Cost Curve",
            xaxis_title="Number of Users",
            yaxis_title="Monthly Cost (USD)",
            plot_bgcolor=REDSAND_GREY,
            paper_bgcolor=REDSAND_GREY,
            font=dict(color=REDSAND_DARK)
        )
        st.plotly_chart(fig_curve, use_container_width=True)

else:
    st.info("Please select a valid GPU configuration to view the cost and scaling analysis.")
