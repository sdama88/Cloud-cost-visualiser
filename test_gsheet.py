import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)

SHEET_ID = "1_12UkneY5K6f9RCdgh0PgscbIA0mhnKN"

try:
    spreadsheet = client.open_by_key(SHEET_ID)
    st.success("✅ Connected to Google Sheet!")

    worksheets = spreadsheet.worksheets()
    st.write("Worksheets:", [ws.title for ws in worksheets])

    ws = worksheets[0]
    data = ws.get_all_records()
    st.dataframe(pd.DataFrame(data).head())

except Exception as e:
    import traceback
    st.error("❌ Could not connect to the sheet")
    st.code(traceback.format_exc())  # full stack trace + Google error
