import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from PIL import Image
import base64
import matplotlib.pyplot as plt
import math

# ---------------------
# CONFIG
# ---------------------
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"  # Replace with your Google Sheet ID
WORKLOADS_SHEET = "workloads"
PRICING_SHEET = "pricing"

SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# Connect to Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], SCOPE
)
client = gspread.authorize(creds)

def load_sheet(sheet_name):
    ws = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)

# Load Data
workloads_df = load_sheet(WORKLOADS_SHEET)
pricing_df = load_sheet(PRICING_SHEET)

# ---------------------
# LOGO
# ---------------------
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()
st.markdown(
    f"""
    <a href="https://redsand.ai" target="_blank">
        <img src="data:image/png;base64,{img_str}" width="120">
    </a>
    """,
    unsafe_allow_html=True,
)

st.title("☁️ Cloud GPU Cost Visualiser")

# ---------------------
# Step 1 - Select workload & users
# ---------------------
workload_name = st.selectbox("Select Workload", sorted(workloads_df["workload_name"].unique()))
num_users = st.slider(
    "Number of Users", 
    min_value=10, 
    max_value=10000, 
    step=10, 
    value=100
)

# Filter workloads for this selection
possible_configs = workloads_df[workloads_df["workload_name"] == workload_name]

# Auto-select GPU config based on highest efficiency (users_per_gpu)
best_config = possible_configs.loc[possible_configs["users_per_gpu"].idxmax()]

# Calculate required GPUs
required_gpus_auto = math.ceil(num_users / best_config["users_per_gpu"])

# ---------------------
# Step 2 - Manual override
# ---------------------
st.subheader("GPU Configuration")
manual_mode = st.checkbox("Manually select GPU type and number of GPUs", value=False)

if manual_mode:
    gpu_type = st.selectbox("GPU Type", sorted(workloads_df["gpu_type"].unique()))
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=required_gpus_auto)
    chosen_config = possible_configs[possible_configs["gpu_type"] == gpu_type].iloc[0]
    if num_users > chosen_config["users_per_gpu"] * num_gpus:
        st.warning("⚠️ This configuration may be underpowered for the selected number of users.")
else:
    gpu_type = best_config["gpu_type"]
    num_gpus = required_gpus_auto

# ---------------------
# Step 3 - Load & egress calculation
# ---------------------
workload_row = possible_configs[possible_configs["gpu_type"] == gpu_type].iloc[0]

# Storage
total_storage_gb = (
    workload_row["storage_gb_per_gpu_base"] * num_gpus +
    workload_row["storage_gb_per_user"] * num_users
)

# Egress
total_egress_gb = (
    workload_row["egress_gb_per_gpu_base"] * num_gpus +
    workload_row["egress_gb_per_user"] * num_users
)

# ---------------------
# Step 4 - Pricing
# ---------------------
price_row = pricing_df[pricing_df["gpu_type"] == gpu_type].iloc[0]

gpu_hourly = price_row["gpu_hourly_usd"]
storage_price = price_row["storage_price_per_gb_month"]
egress_price = price_row["egress_price_per_gb"]

gpu_monthly_cost = gpu_hourly * 24 * 30 * num_gpus
storage_monthly_cost = total_storage_gb * storage_price
egress_monthly_cost = total_egress_gb * egress_price

total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

# ---------------------
# Step 5 - Display results
# ---------------------
st.subheader("📊 Cost Summary")
st.write(f"**GPU Type:** {gpu_type}")
st.write(f"**Number of GPUs:** {num_gpus}")
st.write(f"**Total Storage:** {total_storage_gb:,.0f} GB")
st.write(f"**Total Egress:** {total_egress_gb:,.0f} GB/month")
st.write(f"**Total Monthly Cost:** ${total_monthly_cost:,.2f}")

# Chart
fig, ax = plt.subplots()
ax.bar(["GPU Cost", "Storage Cost", "Egress Cost"], 
       [gpu_monthly_cost, storage_monthly_cost, egress_monthly_cost],
       color=["#FF4B4B", "#4BB3FF", "#FFD34B"])
ax.set_ylabel("USD")
ax.set_title("Monthly Cost Breakdown")
st.pyplot(fig)

# ---------------------
# Footnote
# ---------------------
st.markdown("""
<small>* Pricing is aggregated and indicative only. Actual cloud provider pricing may vary based on contracts, reserved instances, and regional rates. *</small>
""", unsafe_allow_html=True)
