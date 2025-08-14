import streamlit as st
import pandas as pd
import math
import gspread
from google.oauth2 import service_account
from PIL import Image
from io import BytesIO
import base64

# ======= CONFIG =======
st.set_page_config(page_title="Cloud AI Cost Visualiser", layout="wide")

# ======= LOGO BASE64 ENCODE =======
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.markdown(
        f'<a href="https://redsand.ai" target="_blank">'
        f'<img src="data:image/png;base64,{img_str}" width="80"></a>',
        unsafe_allow_html=True
    )
with col2:
    st.markdown("<h1 style='margin-bottom:0;'>Cloud AI Cost Visualiser</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:gray;'>Estimate your monthly cloud AI costs based on workload and user load.</p>", unsafe_allow_html=True)

# ======= GOOGLE SHEET CONFIG =======
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
WORKLOADS_SHEET = "workloads"
PRICING_SHEET = "pricing"

# Authenticate with GCP
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)

# ======= HELPER TO LOAD SHEET =======
def load_sheet(sheet_name):
    ws = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\n', '')
    return df

# ======= LOAD DATA =======
workloads_df = load_sheet(WORKLOADS_SHEET)
pricing_df = load_sheet(PRICING_SHEET)

# ======= INPUTS =======
selected_workload = st.selectbox("Select Workload", workloads_df["workload_name"].unique())
workload_row = workloads_df[workloads_df["workload_name"] == selected_workload].iloc[0]

model_name = workload_row["model_name"]
gpu_type = workload_row["gpu_type"]
base_gpus = workload_row["base_gpus"]
users_per_gpu = workload_row["users_per_gpu"]
storage_gb_per_gpu = workload_row["storage_gb_per_gpu"]
egress_gb_per_gpu_base = workload_row["egress_gb_per_gpu"]
egress_gb_per_user = workload_row["egress_gb_per_user"]

# Pricing from same sheet
gpu_row = pricing_df[pricing_df["gpu_type"] == gpu_type].iloc[0]
gpu_hourly = gpu_row["gpu_hourly_usd"]
storage_price_per_gb = gpu_row["storage_price_per_gb_month"]
egress_price_per_gb = gpu_row["egress_price_per_gb"]

# Fixed constants
hours_per_month = 730
currency = "USD"

# ======= SLIDER =======
max_users = 1000
num_users = st.slider("Number of Users", min_value=1, max_value=max_users, value=100)

# ======= COST CALC =======
gpu_count = max(base_gpus, math.ceil(num_users / users_per_gpu))
compute_cost = gpu_count * gpu_hourly * hours_per_month
storage_cost = gpu_count * storage_gb_per_gpu * storage_price_per_gb
egress_cost = (gpu_count * egress_gb_per_gpu_base + (egress_gb_per_user * num_users)) * egress_price_per_gb
total_cost = compute_cost + storage_cost + egress_cost

# ======= DISPLAY COST =======
st.markdown(f"## Estimated Monthly Cost: **{currency} {total_cost:,.2f}**")
st.caption("Includes compute, storage, and egress costs. Prices are estimates and may vary.")

# ======= STACKED COST BREAKDOWN GRAPH =======
user_range = list(range(1, max_users + 1))
compute_list = []
storage_list = []
egress_list = []

for u in user_range:
    g_count = base_gpus * (u / (users_per_gpu * base_gpus))
    g_count = max(base_gpus, g_count)

    comp = g_count * gpu_hourly * hours_per_month
    store = g_count * storage_gb_per_gpu * storage_price_per_gb
    egress = (g_count * egress_gb_per_gpu_base + (egress_gb_per_user * u)) * egress_price_per_gb

    compute_list.append(comp)
    storage_list.append(store)
    egress_list.append(egress)

chart_df = pd.DataFrame({
    "Compute Cost": compute_list,
    "Storage Cost": storage_list,
    "Egress Cost": egress_list
}, index=user_range)

st.area_chart(chart_df)

# ======= FOOTNOTE =======
st.markdown("---")
st.caption("*This tool is for illustrative purposes. Actual costs may vary by cloud provider, workload configuration, and usage patterns.*")
