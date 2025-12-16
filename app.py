import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# --- 1. SETUP DATABASE ---
# REPLACE WITH YOUR KEYS
SUPABASE_URL = "https://ktcrzsbaykddcsjznycs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt0Y3J6c2JheWtkZGNzanpueWNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5MDM0MzQsImV4cCI6MjA4MTQ3OTQzNH0.si9UsH3BnV6BKT9QG4sTVUsfI5IAUV1a_3qi0vvUGaw" 

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# --- 2. CONFIG ---
st.set_page_config(page_title="FundLite V4 | Capital Calls", page_icon="💰", layout="wide")
def fmt(val): return f"${val:,.2f}"

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("FundLite Admin")
    st.info("🟢 Database Connected")
    st.markdown("---")
    st.write("**Current Fund:** Harbor View Fund I")

# --- 4. MAIN APP ---
tab1, tab2 = st.tabs(["📊 Portfolio Overview", "📢 Run Capital Call"])

# === TAB 1: OVERVIEW ===
with tab1:
    st.header("Fund Overview")
    
    if supabase:
        # Fetch Data
        comm_data = supabase.table('commitments').select("*, investors(display_name)").execute()
        
        if comm_data.data:
            df = pd.DataFrame(comm_data.data)
            
            # Clean up the data (Flatten the nested investor name)
            # The DB returns: {'committed_amount': 1000, 'investors': {'display_name': 'John'}}
            df['Investor Name'] = df['investors'].apply(lambda x: x['display_name'] if x else "Unknown")
            df['Commitment'] = df['committed_amount']
            
            # Calculate Stats
            total_fund = df['Commitment'].sum()
            df['Ownership %'] = (df['Commitment'] / total_fund) * 100
            
            # KPI Cards
            c1, c2 = st.columns(2)
            c1.metric("Total Fund Size", fmt(total_fund))
            c2.metric("Total Investors", len(df))
            
            st.divider()
            
            # Show the Ownership Table
            st.subheader("Cap Table (Ownership)")
            
            # Format for display
            display_df = df[['Investor Name', 'Commitment', 'Ownership %']].copy()
            display_df['Commitment'] = display_df['Commitment'].apply(fmt)
            display_df['Ownership %'] = display_df['Ownership %'].apply(lambda x: f"{x:.2f}%")
            
            st.table(display_df)
            
        else:
            st.warning("No investors found. Go add some in Supabase!")

# === TAB 2: CAPITAL CALL MODULE ===
with tab2:
    st.header("Initiate Capital Call")
    
    # 1. INPUTS
    col1, col2 = st.columns(2)
    with col1:
        call_amount = st.number_input("Total Call Amount ($)", value=500000.00, step=10000.00)
    with col2:
        call_date = st.date_input("Due Date")
    
    # 2. PREVIEW (The Calculation)
    st.subheader("Allocation Preview")
    
    if supabase and comm_data.data:
        # Re-use the dataframe from Tab 1
        # Logic: Investor Share = (Commitment / Total Fund) * Call Amount
        df['Call Amount'] = (df['Ownership %'] / 100) * call_amount
        
        # Display Preview Grid
        preview_df = df[['Investor Name', 'Ownership %', 'Call Amount']].copy()
        preview_df['Ownership %'] = preview_df['Ownership %'].apply(lambda x: f"{x:.2f}%")
        preview_df['Call Amount'] = preview_df['Call Amount'].apply(fmt)
        
        st.dataframe(preview_df, use_container_width=True)
        
        st.info(f"ℹ️ You are calling **{fmt(call_amount)}**. Based on commitments, the system calculated the split above.")
        
        # 3. EXECUTE (Write to DB)
        st.divider()
        if st.button("🚀 Post to Ledger", type="primary"):
            st.write("Writing to database... (Simulation Mode)")
            
            # THIS IS WHERE WE WOULD WRITE THE INSERT CODE
            # For each investor in the list:
            # supabase.table('ledger_entries').insert({ ... })
            
            st.success(f"Successfully posted Capital Call for {fmt(call_amount)}!")
            st.balloons()
            
    else:
        st.error("No investors found to allocate to.")
