import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
from io import BytesIO
from PIL import Image
import math
import matplotlib.pyplot as plt

# ===== CONFIG =====
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
WORKLOAD_SHEET = "workloads"
PRICING_SHEET = "pricing"

# Brand Colors
REDSAND_RED = "#C2634B"
REDSAND_BG = "#F5F1EE"
TEXT_DARK = "#222222"

# ===== AUTHENTICATE TO GOOGLE SHEETS =====
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], SCOPE
)
client = gspread.authorize(creds)

# ===== FUNCTIONS =====
def load_sheet(sheet_name):
    ws = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip()
    return df

# ===== LOAD DATA =====
workloads_df = load_sheet(WORKLOAD_SHEET)
pricing_df = load_sheet(PRICING_SHEET)

# ===== PAGE CONFIG =====
st.set_page_config(page_title="Cloud GPU Cost Visualiser", layout="wide")

# ===== LOGO =====
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:20px;">
        <a href="https://redsand.ai" target="_blank">
            <img src="data:image/png;base64,{img_str}" width="80">
        </a>
        <h1 style="color:{TEXT_DARK};">☁️ Cloud GPU Cost Visualiser</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# ===== STEP 1: SELECT WORKLOAD =====
workload = st.selectbox("Select Workload", workloads_df["workload_name"].unique())

# ===== STEP 2: NUMBER OF USERS =====
num_users = st.slider(
    "Number of Users", min_value=10, max_value=10000, step=10, value=100
)

# ===== FILTER WORKLOAD =====
workload_row = workloads_df[workloads_df["workload_name"] == workload].iloc[0]

# ===== STEP 3: MANUAL GPU CONFIG OPTION =====
manual_config = st.checkbox("Manually select GPU type and number of GPUs")

if manual_config:
    gpu_type = st.selectbox("Select GPU Type", pricing_df["gpu_type"].unique())
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=1)
else:
    # Auto selection logic
    gpu_type = workload_row["gpu_type"]
    base_gpus = workload_row["base_gpus"]
    users_per_gpu = workload_row["users_per_gpu"]
    num_gpus = math.ceil(num_users / users_per_gpu)

# ===== COST CALCULATIONS =====
gpu_price_hr = pricing_df.loc[
    pricing_df["gpu_type"] == gpu_type, "gpu_hourly_usd"
].values[0]
storage_price_gb = pricing_df.loc[
    pricing_df["gpu_type"] == gpu_type, "storage_price_per_gb_month"
].values[0]
egress_price_gb = pricing_df.loc[
    pricing_df["gpu_type"] == gpu_type, "egress_price_per_gb"
].values[0]

storage_gb_per_gpu = workload_row["storage_gb_per_gpu"]
egress_gb_per_gpu = workload_row["egress_gb_per_gpu"]

total_storage_gb = storage_gb_per_gpu * num_gpus
total_egress_gb = egress_gb_per_gpu * num_gpus

gpu_monthly = gpu_price_hr * 24 * 30 * num_gpus
storage_monthly = total_storage_gb * storage_price_gb
egress_monthly = total_egress_gb * egress_price_gb

total_monthly_cost = gpu_monthly + storage_monthly + egress_monthly

# ===== BIG RED COST DISPLAY =====
st.markdown(
    f"<h1 style='color:{REDSAND_RED}; font-size: 64px; text-align: center;'>${total_monthly_cost:,.2f} / month</h1>",
    unsafe_allow_html=True
)

# ===== GPU CONFIG CARDS =====
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"<div style='background-color:{REDSAND_BG}; padding:20px; border-radius:10px;'>"
        f"<h4 style='color:{REDSAND_RED};'>GPU Type</h4><p style='font-size:18px; color:{TEXT_DARK};'>{gpu_type}</p></div>",
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f"<div style='background-color:{REDSAND_BG}; padding:20px; border-radius:10px;'>"
        f"<h4 style='color:{REDSAND_RED};'>Number of GPUs</h4><p style='font-size:18px; color:{TEXT_DARK};'>{num_gpus}</p></div>",
        unsafe_allow_html=True
    )
with col3:
    st.markdown(
        f"<div style='background-color:{REDSAND_BG}; padding:20px; border-radius:10px;'>"
        f"<h4 style='color:{REDSAND_RED};'>Users</h4><p style='font-size:18px; color:{TEXT_DARK};'>{num_users}</p></div>",
        unsafe_allow_html=True
    )

# ===== COST BREAKDOWN CHART =====
cost_data = pd.DataFrame({
    "Category": ["GPU", "Storage", "Egress"],
    "Cost": [gpu_monthly, storage_monthly, egress_monthly]
})

fig, ax = plt.subplots(figsize=(5,4))
bars = ax.bar(cost_data["Category"], cost_data["Cost"], color=REDSAND_RED)
ax.set_title("Monthly Cost Breakdown", color=TEXT_DARK, fontsize=14)
ax.set_ylabel("Cost (USD)", color=TEXT_DARK)
ax.bar_label(bars, fmt="$%.0f", label_type="edge")
st.pyplot(fig)

# ===== FOOTNOTE =====
st.markdown(
    "<p style='font-size:12px; color:gray;'>*Based on average market rates for equivalent compute. Storage and egress are estimated based on workload type.</p>",
    unsafe_allow_html=True
)
