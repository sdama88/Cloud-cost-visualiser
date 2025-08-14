import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import base64
from io import BytesIO

# -------------------
# CONFIG
# -------------------
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
WORKLOADS_SHEET = "workloads"
PRICING_SHEET = "pricing"

BRAND_RED = "#D62828"
BRAND_DARK_RED = "#A31621"
BRAND_LIGHT = "#F5F5F5"

# -------------------
# GOOGLE SHEET ACCESS
# -------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)

def load_sheet(sheet_name):
    ws = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)

workloads_df = load_sheet(WORKLOADS_SHEET)
pricing_df = load_sheet(PRICING_SHEET)

# -------------------
# LOGO
# -------------------
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

# -------------------
# PAGE CONFIG
# -------------------
st.set_page_config(
    page_title="Cloud GPU Cost Visualiser",
    layout="wide"
)

st.markdown(
    f"""
    <style>
        .main {{
            background: linear-gradient(to bottom right, white, {BRAND_LIGHT});
        }}
        .big-cost {{
            font-size: 48px;
            font-weight: bold;
            color: {BRAND_RED};
            text-align: center;
            animation: pulse 1.5s ease-in-out infinite alternate;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            100% {{ transform: scale(1.05); }}
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------
# HEADER
# -------------------
col1, col2 = st.columns([1,5])
with col1:
    st.markdown(f'<a href="https://redsand.ai"><img src="data:image/png;base64,{img_str}" width="100"></a>', unsafe_allow_html=True)
with col2:
    st.title("☁️ Cloud GPU Cost Visualiser")

# -------------------
# CONTROL PANEL
# -------------------
col1, col2, col3 = st.columns([2,2,2])

with col1:
    workload_choice = st.selectbox("Select Workload", workloads_df["workload_name"].unique())

with col2:
    num_users = st.slider("Number of Users", 10, 10000, 100, step=10 if 100 >= 10 else 100)

with col3:
    manual_mode = st.toggle("Manual GPU Selection", value=False)

workload_row = workloads_df[workloads_df["workload_name"] == workload_choice].iloc[0]

if manual_mode:
    gpu_type = st.selectbox("GPU Type", pricing_df["gpu_type"].unique())
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=int(workload_row["base_gpus"]))
else:
    gpu_type = workload_row["gpu_type"]
    num_gpus = max(1, int(np.ceil(num_users / workload_row["users_per_gpu"])))

# Warning if config might be underpowered
required_gpus = np.ceil(num_users / workload_row["users_per_gpu"])
if manual_mode and num_gpus < required_gpus:
    st.warning(f"⚠️ This configuration may be underpowered for {num_users} users. Recommended: {int(required_gpus)}+ GPUs.")

# -------------------
# COST CALCULATION
# -------------------
gpu_hourly = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "egress_price_per_gb"].values[0]

storage_gb = num_gpus * workload_row["storage_gb_per_gpu"]
egress_gb = num_gpus * workload_row["egress_gb_per_gpu_base"] + num_users * workload_row["egress_gb_per_user"]

gpu_monthly = gpu_hourly * 24 * 30 * num_gpus
storage_monthly = storage_price * storage_gb
egress_monthly = egress_price * egress_gb
total_monthly = gpu_monthly + storage_monthly + egress_monthly

# -------------------
# BIG COST DISPLAY WITH ANIMATION
# -------------------
placeholder = st.empty()
old_value = 0
for val in np.linspace(old_value, total_monthly, 20):
    placeholder.markdown(f"<div class='big-cost'>${val:,.0f} / month</div>", unsafe_allow_html=True)
    time.sleep(0.05)

# -------------------
# COST BREAKDOWN CHART
# -------------------
fig, ax = plt.subplots(figsize=(6,4))
costs = [gpu_monthly, storage_monthly, egress_monthly]
labels = ["GPU", "Storage", "Egress"]
colors = [BRAND_RED, "#E56B6F", "#FAA307"]

ax.bar(labels, costs, color=colors)
ax.set_ylabel("USD / month")
ax.set_title("Cost Breakdown")
st.pyplot(fig)

# -------------------
# FOOTNOTES
# -------------------
st.markdown(
    """
    **Notes:**  
    *Pricing is based on current public cloud rates and may vary.*  
    *Egress costs are estimated based on workload usage patterns.*  
    """,
    unsafe_allow_html=True
)
