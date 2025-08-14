import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import math
from PIL import Image
from io import BytesIO
import base64

# ======= SETTINGS =======
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
WORKLOADS_SHEET = "workloads"
PRICING_SHEET = "pricing"
CONFIG_SHEET = "config"

# ======= GOOGLE SHEETS CONNECTION =======
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
client = gspread.authorize(credentials)

def load_sheet(sheet_name):
    ws = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip().str.replace('\u200b', '').str.lower()
    return df

workloads_df = load_sheet(WORKLOADS_SHEET)
pricing_df = load_sheet(PRICING_SHEET)
config_df = load_sheet(CONFIG_SHEET)

# ======= CONFIG SETTINGS =======
hours_per_month = int(config_df.loc[config_df['setting_name'] == 'hours_per_month', 'value'].values[0])
default_workload = config_df.loc[config_df['setting_name'] == 'default_workload', 'value'].values[0]
max_users = int(config_df.loc[config_df['setting_name'] == 'max_users', 'value'].values[0])
currency = config_df.loc[config_df['setting_name'] == 'currency', 'value'].values[0]

# ======= PAGE CONFIG =======
st.set_page_config(page_title="Cloud AI Cost Visualiser", layout="wide")

# ======= LOGO BASE64 ENCODE =======
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

# ======= HEADER =======
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

st.markdown("<hr style='border: 1px solid #444;'>", unsafe_allow_html=True)

# ======= USER INPUTS =======
selected_workload = st.selectbox("Select workload", workloads_df['workload_name'].unique(), index=list(workloads_df['workload_name']).index(default_workload))
num_users = st.slider("Number of concurrent users", 1, max_users, 50)

# ======= CALCULATIONS =======
workload_row = workloads_df[workloads_df['workload_name'] == selected_workload].iloc[0]
gpu_type = workload_row["gpu_type"]
base_gpus = int(workload_row["base_gpus"])
users_per_gpu = int(workload_row["users_per_gpu"])
storage_gb_per_gpu = float(workload_row["storage_gb_per_gpu"])
egress_gb_per_gpu_base = float(workload_row["egress_gb_per_gpu_base"])
egress_gb_per_user = float(workload_row["egress_gb_per_user"])

gpu_count = max(base_gpus, math.ceil(num_users / users_per_gpu))

pricing_row = pricing_df[pricing_df['gpu_type'] == gpu_type].iloc[0]
gpu_hourly = float(pricing_row["blended_hourly_usd"])
storage_price_per_gb = float(pricing_row["storage_price_per_gb_month"])
egress_price_per_gb = float(pricing_row["egress_price_per_gb"])

compute_cost = gpu_count * gpu_hourly * hours_per_month
total_storage_gb = gpu_count * storage_gb_per_gpu
storage_cost = total_storage_gb * storage_price_per_gb
total_egress_gb = gpu_count * egress_gb_per_gpu_base + (egress_gb_per_user * num_users)
egress_cost = total_egress_gb * egress_price_per_gb

total_cost = compute_cost + storage_cost + egress_cost

# ======= COST DISPLAY =======
st.markdown(f"<h2 style='color:red;'>{currency} {total_cost:,.0f} / month</h2>", unsafe_allow_html=True)

colA, colB, colC = st.columns(3)
colA.metric("Compute Cost", f"{currency} {compute_cost:,.0f}")
colB.metric("Storage Cost", f"{currency} {storage_cost:,.0f}")
colC.metric("Egress Cost", f"{currency} {egress_cost:,.0f}")

st.write(f"**GPU Type:** {gpu_type} | **GPUs Used:** {gpu_count}")

# ======= STREAMLIT NATIVE GRAPH =======
user_range = list(range(1, max_users + 1))
costs = []
for u in user_range:
    g_count = max(base_gpus, math.ceil(u / users_per_gpu))
    comp = g_count * gpu_hourly * hours_per_month
    store = g_count * storage_gb_per_gpu * storage_price_per_gb
    egress = (g_count * egress_gb_per_gpu_base + (egress_gb_per_user * u)) * egress_price_per_gb
    costs.append(comp + store + egress)

st.line_chart(pd.DataFrame({
    f"Monthly Cost ({currency})": costs
}, index=user_range))

# ======= FOOTNOTE =======
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='font-size:12px;color:gray;'>* This tool provides an aggregated estimate based on typical cloud pricing and workload profiles. Actual costs may vary depending on provider, region, and usage patterns.</p>", unsafe_allow_html=True)
