import streamlit as st
import pandas as pd
import math
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
from io import BytesIO
import base64

# Streamlit page setup
st.set_page_config(page_title="Cloud Cost Visualiser", layout="wide")

# Load logo as Base64 and make it clickable
logo = Image.open("logo.png")
buff = BytesIO()
logo.save(buff, format="PNG")
img_str = base64.b64encode(buff.getvalue()).decode()
st.markdown(f'''
<a href="https://redsand.ai" target="_blank">
  <img src="data:image/png;base64,{img_str}" width="80">
</a>
''', unsafe_allow_html=True)
st.markdown("<h1>Cloud Cost Visualiser</h1>", unsafe_allow_html=True)

# Google Sheets setup
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"],
                                              scopes=["https://spreadsheets.google.com/feeds",
                                                      "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)

def load_sheet(name):
    ws = client.open_by_key(SHEET_ID).worksheet(name)
    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace('\n', '')
    return df

workloads_df = load_sheet("workloads")
pricing_df = load_sheet("pricing")

def safe_get(row, col, default=0):
    return row[col] if col in row.index else default

# Workload selection
workload_name = st.selectbox("Select workload and GPU combo:", workloads_df["workload_name"] + " — " + workloads_df["gpu_type"])
idx = workloads_df.index[workloads_df["workload_name"] + " — " + workloads_df["gpu_type"] == workload_name][0]
wl = workloads_df.loc[idx]

gpu_mode = st.radio("GPU Selection Mode", ("Auto", "Manual"), horizontal=True)
if gpu_mode == "Auto":
    gpu_type = wl["gpu_type"]
else:
    gpu_type = st.selectbox("Select GPU Type:", pricing_df["gpu_type"])

# Workload parameters
base_gpus = int(wl["base_gpus"])
users_per_gpu = int(wl["users_per_gpu"])
storage_gb_per_gpu = int(wl["storage_gb_per_gpu"])
egress_base = safe_get(wl, "egress_gb_per_gpu_base", 0)
egress_per_user = safe_get(wl, "egress_gb_per_user", 0)
num_users = st.slider("Number of Concurrent Users", 1, 10000, 500, step=50)

# Pricing
pr = pricing_df[pricing_df["gpu_type"] == gpu_type].iloc[0]
gpu_hr = pr["gpu_hourly_usd"]
store_pr = pr["storage_price_per_gb_month"]
egress_pr = pr["egress_price_per_gb"]

# Compute costs
req_gpus = max(base_gpus, math.ceil(num_users / users_per_gpu))
gpu_cost = req_gpus * gpu_hr * 24 * 30
store_cost = req_gpus * storage_gb_per_gpu * store_pr
egress_cost = (req_gpus * egress_base + num_users * egress_per_user) * egress_pr
total = gpu_cost + store_cost + egress_cost

# Display result
st.markdown(f"### Estimated Monthly Cost: **${total:,.2f}** (GPUs: {req_gpus}, Type: {gpu_type})")

# Graph of cost vs users
usr = list(range(1, 10001, 500))
costs = []
for u in usr:
    g = max(base_gpus, math.ceil(u / users_per_gpu))
    c = (g * gpu_hr * 24 * 30) + (g * storage_gb_per_gpu * store_pr) + ((g * egress_base + u * egress_per_user) * egress_pr)
    costs.append(c)
dfc = pd.DataFrame({"Users": usr, "Total Cost": costs}).set_index("Users")
st.area_chart(dfc)

st.markdown("*Estimates only. Real costs depend on region, discounts, and provider nuances.*")
