import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Google Sheets API scope
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authenticate using secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)

# Use your sheet ID
SHEET_ID = "1_12UkneY5K6f9RCdgh0PgscbIA0mhnKN"

try:
    spreadsheet = client.open_by_key(SHEET_ID)
    st.success("✅ Successfully connected to Google Sheet!")

    # List worksheet names
    worksheets = spreadsheet.worksheets()
    st.write("Worksheets in the sheet:", [ws.title for ws in worksheets])

    # Try reading the first worksheet
    ws = worksheets[0]
    data = ws.get_all_records()
    st.write("First few rows:", pd.DataFrame(data).head())

except Exception as e:
    st.error(f"❌ Could not connect to the sheet: {e}")
