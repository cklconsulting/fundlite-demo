import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
# --- NEW IMPORT FOR DATABASE ---
from supabase import create_client, Client

# --- 1. SETUP DATABASE CONNECTION ---
# REPLACE THESE WITH YOUR ACTUAL SUPABASE KEYS
SUPABASE_URL = "https://ktcrzsbaykddcsjznycs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt0Y3J6c2JheWtkZGNzanpueWNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5MDM0MzQsImV4cCI6MjA4MTQ3OTQzNH0.si9UsH3BnV6BKT9QG4sTVUsfI5IAUV1a_3qi0vvUGaw"

# Initialize the connection (Cached so it doesn't reconnect every click)
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="FundLite V3 | Database Connected", page_icon="📊", layout="wide")

# --- 3. HELPER FUNCTIONS ---
def fmt(value):
    return f"${value:,.2f}"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("FundLite Admin")
    st.info("🟢 Database Status: Connected")
    
    if supabase is None:
        st.error("❌ Connection Failed. Check URL/Key in code.")

# --- 5. MAIN TABS ---
tab1, tab2 = st.tabs(["📝 Real Data (From DB)", "💸 The Dashboard"])

# === TAB 1: THE DATABASE VIEW ===
with tab1:
    st.header("Live Database Records")
    st.markdown("This data is coming directly from your **Supabase Cloud Database**, not from the code.")
    
    if supabase:
        # QUERY 1: Fetch Funds
        st.subheader("1. Funds Table")
        response_funds = supabase.table('funds').select("*").execute()
        if response_funds.data:
            st.dataframe(pd.DataFrame(response_funds.data))
        else:
            st.warning("No Funds found. Go add one in Supabase!")

        st.divider()

        # QUERY 2: Fetch Commitments
        st.subheader("2. Commitments Table")
        response_comm = supabase.table('commitments').select("*").execute()
        
        if response_comm.data:
            # Load into a clean table
            df_comm = pd.DataFrame(response_comm.data)
            st.dataframe(df_comm)
            
            # CALCULATE TOTAL (The Logic)
            total_committed = df_comm['committed_amount'].sum()
            st.success(f"✅ Total Capital Committed (Calculated from DB): **{fmt(total_committed)}**")
        else:
            st.warning("No Commitments found.")

# === TAB 2: THE DASHBOARD ===
with tab2:
    st.header("Investor Portal")
    # If we have data, use it. If not, show 0.
    real_commitment = 0
    if supabase:
        resp = supabase.table('commitments').select("committed_amount").execute()
        if resp.data:
            real_commitment = sum(item['committed_amount'] for item in resp.data)
    
    col1, col2 = st.columns(2)
    col1.metric("Total Fund Commitments", fmt(real_commitment))
    col2.metric("Active Investors", len(resp.data) if supabase and resp.data else 0)
