from fpdf import FPDF
import tempfile
import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# --- PDF GENERATOR FUNCTION ---
def create_pdf(investor_name, fund_name, balance, transactions):
    # 1. Setup the Page
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 2. Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt=fund_name, ln=True, align='C')
    pdf.set_font("Arial", "I", 10)
    pdf.cell(200, 10, txt="Capital Account Statement", ln=True, align='C')
    pdf.line(10, 30, 200, 30) # Draw a line
    
    # 3. Investor Info
    pdf.ln(10) # Line break
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt=f"Investor: {investor_name}", ln=True)
    pdf.cell(0, 10, txt=f"Date: {date.today()}", ln=True)
    
    # 4. Summary Box
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240) # Light gray background
    pdf.cell(0, 10, txt=f"Ending Capital Balance: {fmt(balance)}", ln=True, fill=True)
    
    # 5. Transaction Table Header
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(80, 10, "Description / Type", 1)
    pdf.cell(40, 10, "Amount", 1, ln=True)
    
    # 6. Table Rows
    pdf.set_font("Arial", "", 10)
    for index, row in transactions.iterrows():
        # Clean up date format
        date_str = str(row['created_at'])[:10] 
        pdf.cell(40, 10, date_str, 1)
        pdf.cell(80, 10, row['trans_code'], 1)
        pdf.cell(40, 10, fmt(row['amount']), 1, ln=True)
        
    # 7. Output
    # Save to a temporary file buffer so Streamlit can download it
    return pdf.output(dest='S').encode('latin-1')

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
tab1, tab2, tab3 = st.tabs(["📊 Portfolio Overview", "📢 Run Capital Call", "📄 Live PCAP Statement"])

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
        
        # 3. EXECUTE (Real Database Write)
        st.divider()
        if st.button("🚀 Post to Ledger (REAL)", type="primary"):
            
            with st.spinner("Writing to Ledger..."):
                try:
                    # A. CREATE THE BATCH (The "Folder" for these transactions)
                    batch_data = {
                        "batch_date": str(call_date),
                        "description": f"Capital Call: {fmt(call_amount)}",
                        "status": "POSTED"
                    }
                    # Insert and get the new Batch ID back
                    batch_resp = supabase.table('batches').insert(batch_data).execute()
                    new_batch_id = batch_resp.data[0]['id']
                    
                    # B. PREPARE THE LEDGER ENTRIES
                    entries_to_insert = []
                    
                    # Loop through our calculated dataframe
                    for index, row in df.iterrows():
                        entry = {
                            "batch_id": new_batch_id,
                            "commitment_id": row['id'],      # The Investor's Contract ID
                            "trans_code": "CC-PRIN",         # Code for "Principal Call"
                            "amount": row['Call Amount']     # Their calculated share
                        }
                        entries_to_insert.append(entry)
                    
                    # C. BULK INSERT (One command to save them all)
                    supabase.table('ledger_entries').insert(entries_to_insert).execute()
                    
                    st.success(f"✅ Success! Posted Batch #{new_batch_id[:8]}...")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Database Error: {str(e)}")
            
    else:
        st.error("No investors found to allocate to.")


# === TAB 3: LIVE PCAP STATEMENT ===
with tab3:
    st.header("Partner Capital Account (Live)")
    st.markdown("Select an investor to view their real-time ledger generated from the database.")
    
    # Check if we have data before trying to run logic
    if supabase and 'comm_data' in locals() and comm_data.data:
        
        # 1. SELECTOR: Choose who to look at
        # We create a dictionary to map Name -> Commitment ID
        investor_map = {row['Investor Name']: row['id'] for index, row in df.iterrows()}
        selected_investor = st.selectbox("Select Investor:", list(investor_map.keys()))
        selected_comm_id = investor_map[selected_investor]
        
        st.divider()
        
        # 2. QUERY: Fetch only THIS investor's ledger entries
        response_ledger = supabase.table('ledger_entries')\
            .select("*")\
            .eq('commitment_id', selected_comm_id)\
            .execute()
            
        if response_ledger.data:
            df_ledger = pd.DataFrame(response_ledger.data)
            
            # 3. MATH: Calculate the Roll-Forward
            # Sum up all "CC-PRIN" transactions
            contributions = df_ledger[df_ledger['trans_code'] == 'CC-PRIN']['amount'].sum()
            
            # Sum up distributions (none yet, but we handle the logic)
            # Use .get() in case the column doesn't exist yet to prevent crashes
            distributions = 0
            if not df_ledger.empty:
                 # Check for distribution codes if you had them
                 pass
            
            ending_balance = contributions - distributions
            
            # 4. DISPLAY: The Statement Header
            c1, c2, c3 = st.columns(3)
            c1.metric("Beginning Balance", "$0.00")
            c2.metric("Contributions", fmt(contributions))
            c3.metric("Ending Capital", fmt(ending_balance))
            
            st.markdown("### Transaction History")
            
            # Clean up the table for display
            display_ledger = df_ledger[['created_at', 'trans_code', 'amount']].copy()
            # Convert amount to currency string
            display_ledger['amount'] = display_ledger['amount'].apply(fmt)
            
            st.table(display_ledger)
            
            # ... (This goes after st.table) ...
            
            st.divider()
            
            # GENERATE PDF BUTTON
            st.subheader("Official Documents")
            
            # Create the PDF in memory
            pdf_bytes = create_pdf(selected_investor, "Harbor View Fund I", ending_balance, df_ledger)
            
            # The Download Button
            st.download_button(
                label="📥 Download Statement (PDF)",
                data=pdf_bytes,
                file_name=f"Statement_{selected_investor}_{date.today()}.pdf",
                mime="application/pdf"
            )            
        else:
            st.info("No transactions found for this investor yet. Go run a Capital Call in Tab 2!")
    else:
        st.warning("No investor data found. Please ensure Supabase is connected and populated.")
        
