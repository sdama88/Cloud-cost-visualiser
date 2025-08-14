import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import math
import altair as alt
from PIL import Image
import base64
from io import BytesIO

# -------------------
# Google Sheets connection
# -------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)

SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
spreadsheet = client.open_by_key(SHEET_ID)

@st.cache_data
def load_data():
    workloads = pd.DataFrame(spreadsheet.worksheet("workloads").get_all_records())
    pricing = pd.DataFrame(spreadsheet.worksheet("pricing").get_all_records())
    config = pd.DataFrame(spreadsheet.worksheet("config").get_all_records())
    return workloads, pricing, config

workloads_df, pricing_df, config_df = load_data()

# -------------------
# Config values
# -------------------
hours_per_month = int(config_df.loc[config_df["setting_name"] == "hours_per_month", "value"].values[0])
default_workload = config_df.loc[config_df["setting_name"] == "default_workload", "value"].values[0]
max_users = int(config_df.loc[config_df["setting_name"] == "max_users", "value"].values[0])
currency = config_df.loc[config_df["setting_name"] == "currency", "value"].values[0]

# -------------------
# Page setup
# -------------------
st.set_page_config(page_title="AI Cloud Cost Visualizer", layout="centered")

# Logo
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: center;">
        <a href="https://redsand.ai" target="_blank">
            <img src="data:image/png;base64,{img_str}" width="100">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

# Styling
st.markdown("""
    <style>
    body {
        background-color: #111111;
        color: #FFFFFF;
    }
    .big-metric {
        font-size: 4em !important;
        font-weight: bold;
        color: #FF0000;
        text-align: center;
    }
    .sub-metric {
        font-size: 1.2em !important;
        color: #AAAAAA;
        text-align: center;
    }
    .tech-detail {
        font-size: 1em !important;
        color: #DDDDDD;
        text-align: center;
        margin-top: -5px;
    }
    .card {
        background-color: #1a1a1a;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .footnote {
        font-size: 0.8em !important;
        color: #777777;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h3 style='text-align:center;'>How much would the cloud charge for your AI?</h3>", unsafe_allow_html=True)

# -------------------
# Inputs in a card
# -------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    workload_names = workloads_df["workload_name"].tolist()
    selected_workload = st.selectbox(
        "Select AI Type",
        workload_names,
        index=workload_names.index(default_workload)
    )
    concurrent_users = st.slider(
        "Concurrent Users",
        min_value=1,
        max_value=max_users,
        value=100,
        step=1
    )
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------
# Calculate cost
# -------------------
workload_row = workloads_df[workloads_df["workload_name"] == selected_workload].iloc[0]
gpu_type = workload_row["gpu_type"]
base_gpus = workload_row["base_gpus"]
users_per_gpu = workload_row["users_per_gpu"]
storage_gb_per_gpu = workload_row["storage_gb_per_gpu"]
egress_gb_per_gpu = workload_row["egress_gb_per_gpu"]

pricing_row = pricing_df[pricing_df["gpu_type"] == gpu_type].iloc[0]
gpu_hourly_rate = pricing_row["blended_hourly_usd"]
storage_price_per_gb = pricing_row["storage_price_per_gb_month"]
egress_price_per_gb = pricing_row["egress_price_per_gb"]

gpu_count = max(base_gpus, math.ceil(concurrent_users / users_per_gpu))
compute_cost = gpu_count * gpu_hourly_rate * hours_per_month
storage_cost = gpu_count * storage_gb_per_gpu * storage_price_per_gb
egress_cost = gpu_count * egress_gb_per_gpu * egress_price_per_gb
total_cost = compute_cost + storage_cost + egress_cost

# -------------------
# Cost display
# -------------------
st.markdown(f"<div class='big-metric'>{currency} {total_cost:,.0f}</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-metric'>Per Month on Cloud*</div>", unsafe_allow_html=True)

# Technical breakdown
st.markdown(f"<div class='tech-detail'><b>GPU Type:</b> {gpu_type} &nbsp; | &nbsp; <b>Number of GPUs:</b> {gpu_count}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='tech-detail'><b>Storage:</b> {gpu_count * storage_gb_per_gpu} GB/month &nbsp; | &nbsp; <b>Egress:</b> {gpu_count * egress_gb_per_gpu} GB/month</div>", unsafe_allow_html=True)

# -------------------
# Chart
# -------------------
chart_data = []
for users in range(1, max_users + 1, max(1, max_users // 50)):
    gpus_needed = max(base_gpus, math.ceil(users / users_per_gpu))
    c_cost = gpus_needed * gpu_hourly_rate * hours_per_month
    s_cost = gpus_needed * storage_gb_per_gpu * storage_price_per_gb
    e_cost = gpus_needed * egress_gb_per_gpu * egress_price_per_gb
    total = c_cost + s_cost + e_cost
    chart_data.append({"Concurrent Users": users, "Monthly Cost": total})

chart_df = pd.DataFrame(chart_data)
line_chart = alt.Chart(chart_df).mark_line(color="#FF0000", strokeWidth=3).encode(
    x=alt.X("Concurrent Users", title="Concurrent Users"),
    y=alt.Y("Monthly Cost", title=f"Monthly Cost ({currency})"),
    tooltip=["Concurrent Users", "Monthly Cost"]
).properties(width=600, height=200)

st.altair_chart(line_chart, use_container_width=True)

# -------------------
# Footnote
# -------------------
st.markdown("<div class='footnote'>*Based on average market rates for equivalent compute. For estimation purposes only.</div>", unsafe_allow_html=True)
