import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import base64
from io import BytesIO
from PIL import Image
import plotly.graph_objects as go

# -------------------------
# CONFIG
# -------------------------
SHEET_ID = "1fz_jPB2GkHgbAhlZmHOr4g0MVQW3Wyw_jg_nLmmkHIk"
WORKLOADS_SHEET = "workloads"
PRICING_SHEET = "pricing"

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# -------------------------
# LOAD GOOGLE SHEETS
# -------------------------
def load_sheet(sheet_name):
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], SCOPE)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    # Clean headers to avoid KeyErrors
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

workloads_df = load_sheet(WORKLOADS_SHEET)
pricing_df = load_sheet(PRICING_SHEET)

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(page_title="Cloud GPU Cost Visualiser", layout="wide")

# Redsand Colors
redsand_red = "#E63946"
redsand_dark = "#1D1D1B"
redsand_light = "#F1FAEE"

# Logo
logo = Image.open("logo.png")
buffered = BytesIO()
logo.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()
st.markdown(
    f"""
    <div style='display:flex;align-items:center;'>
        <a href='https://redsand.ai' target='_blank'>
            <img src='data:image/png;base64,{img_str}' style='height:50px;margin-right:15px;'>
        </a>
        <h2 style='color:{redsand_red};margin:0;'>Cloud GPU Cost Visualiser</h2>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

# -------------------------
# STEP 1: Workload selection
# -------------------------
workload_name = st.selectbox("Select Workload", workloads_df["workload_name"].unique())

# Filter for selected workload
workload_row = workloads_df[workloads_df["workload_name"] == workload_name].iloc[0]

# -------------------------
# STEP 2: Number of Users
# -------------------------
user_options = list(range(10, 110, 10)) + list(range(200, 10001, 100))
num_users = st.select_slider("Number of Users", options=user_options, value=100)

# -------------------------
# STEP 3: Auto or Manual GPU Config
# -------------------------
manual_mode = st.toggle("Manual GPU Selection")

if manual_mode:
    gpu_type = st.selectbox("Select GPU Type", pricing_df["gpu_type"].unique())
    num_gpus = st.number_input("Number of GPUs", min_value=1, value=int(workload_row["base_gpus"]))
else:
    # Auto select based on workload default
    gpu_type = workload_row["gpu_type"]
    users_per_gpu = workload_row["users_per_gpu"]
    num_gpus = max(1, int(num_users / users_per_gpu))

# -------------------------
# STEP 4: Check if config is sufficient
# -------------------------
required_gpus = max(1, int(num_users / workload_row["users_per_gpu"]))
if manual_mode and num_gpus < required_gpus:
    st.error(f"⚠️ Warning: This config may be underpowered. Recommended GPUs: {required_gpus}")

# -------------------------
# STEP 5: Pricing Lookup
# -------------------------
gpu_hourly = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "gpu_hourly_usd"].values[0]
storage_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "storage_price_per_gb_month"].values[0]
egress_price = pricing_df.loc[pricing_df["gpu_type"] == gpu_type, "egress_price_per_gb"].values[0]

# -------------------------
# STEP 6: Usage Calculations
# -------------------------
storage_gb = num_gpus * workload_row["storage_gb_per_gpu"]
egress_gb = (num_gpus * workload_row["egress_gb_per_gpu_base"]) + (num_users * workload_row["egress_gb_per_user"])

gpu_monthly_cost = gpu_hourly * 24 * 30 * num_gpus
storage_monthly_cost = storage_gb * storage_price
egress_monthly_cost = egress_gb * egress_price
total_monthly_cost = gpu_monthly_cost + storage_monthly_cost + egress_monthly_cost

# -------------------------
# STEP 7: Big Animated Cost
# -------------------------
placeholder = st.empty()
for i in range(0, int(total_monthly_cost), max(1, int(total_monthly_cost / 50))):
    placeholder.markdown(
        f"<h1 style='color:{redsand_red};font-size:60px;text-align:center;'>${i:,.0f} / month</h1>",
        unsafe_allow_html=True
    )
    time.sleep(0.02)
placeholder.markdown(
    f"<h1 style='color:{redsand_red};font-size:60px;text-align:center;'>{total_monthly_cost:,.0f} USD / month</h1>",
    unsafe_allow_html=True
)

# -------------------------
# STEP 8: Stacked Cost Chart
# -------------------------
fig = go.Figure(data=[
    go.Bar(name="GPU Cost", x=["Monthly Cost"], y=[gpu_monthly_cost], marker_color=redsand_red),
    go.Bar(name="Storage Cost", x=["Monthly Cost"], y=[storage_monthly_cost], marker_color="#457B9D"),
    go.Bar(name="Egress Cost", x=["Monthly Cost"], y=[egress_monthly_cost], marker_color="#A8DADC")
])
fig.update_layout(barmode='stack', title="Cost Breakdown", plot_bgcolor=redsand_light, paper_bgcolor=redsand_light)

st.plotly_chart(fig, use_container_width=True)

# -------------------------
# STEP 9: Footnotes
# -------------------------
st.markdown(
    """
    <hr>
    <small>
    * All prices are estimates based on current cloud GPU, storage, and egress rates.  
    * Actual costs may vary depending on provider, location, and usage pattern.  
    * Egress and storage scale with number of users and workload type.  
    </small>
    """,
    unsafe_allow_html=True
)
