import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
from fpdf import FPDF
import tempfile

# --- 1. SETUP DATABASE CONNECTION ---
# ⚠️ REPLACE WITH YOUR ACTUAL KEYS
SUPABASE_URL = "https://ktcrzsbaykddcsjznycs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt0Y3J6c2JheWtkZGNzanpueWNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5MDM0MzQsImV4cCI6MjA4MTQ3OTQzNH0.si9UsH3BnV6BKT9QG4sTVUsfI5IAUV1a_3qi0vvUGaw" 

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# --- 2. CONFIG & HELPER FUNCTIONS ---
st.set_page_config(page_title="FundLite | Pro", page_icon="🏦", layout="wide")

def fmt(val):
    # Helper for the PDF generator only
    return f"${val:,.2f}"

def create_pdf(investor_name, fund_name, balance, transactions):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, txt=fund_name, ln=True, align='C')
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 10, txt="Capital Account Statement", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    
    # Info
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt=f"Investor: {investor_name}", ln=True)
    pdf.cell(0, 10, txt=f"Date: {date.today()}", ln=True)
    
    # Summary
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, txt=f"Ending Capital Balance: {fmt(balance)}", ln=True, fill=True)
    
    # Table Header
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 10, "Date", 1)
    pdf.cell(40, 10, "Type", 1)
    pdf.cell(80, 10, "Description", 1)
    pdf.cell(40, 10, "Amount", 1, ln=True, align='R')
    
    # Table Rows
    pdf.set_font("Arial", "", 10)
    for index, row in transactions.iterrows():
        d_str = str(row['date'])
        t_type = str(row['trans_code'])
        desc = "Capital Call"
        # Ensure amount is treated as float for formatting
        amt = fmt(float(row['amount']))
        
        pdf.cell(30, 10, d_str, 1)
        pdf.cell(40, 10, t_type, 1)
        pdf.cell(80, 10, desc, 1)
        pdf.cell(40, 10, amt, 1, ln=True, align='R')
        
    return pdf.output(dest='S').encode('latin-1')

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("FundLite Admin")
    if supabase:
        st.success("🟢 System Online")
    else:
        st.error("🔴 DB Connection Failed")
    st.markdown("---")
    st.write("**Fund:** Harbor View Fund I")

# --- 4. MAIN TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Fund Overview", "📢 Capital Calls", "📄 Live PCAP Statement"])

# === TAB 1: OVERVIEW ===
with tab1:
    st.header("Fund Overview")
    
    if supabase:
        comm_data = supabase.table('commitments').select("*, investors(display_name)").execute()
        
        if comm_data.data:
            df = pd.DataFrame(comm_data.data)
            
            # Logic
            df['Investor Name'] = df['investors'].apply(lambda x: x['display_name'] if x else "Unknown")
            df['Commitment'] = df['committed_amount'] # Keep as FLOAT (Number)
            
            total_fund = df['Commitment'].sum()
            df['Ownership %'] = (df['Commitment'] / total_fund) * 100 # Keep as FLOAT
            
            # KPI Cards
            c1, c2 = st.columns(2)
            c1.metric("Total Fund Size", fmt(total_fund))
            c2.metric("Total Investors", len(df))
            
            st.divider()
            
            # Cap Table
            st.subheader("Cap Table (Ownership)")
            
            display_df = df[['Investor Name', 'Commitment', 'Ownership %']].copy()
            display_df.index = display_df.index + 1
            
            # THE FIX: Use .format() to add style, but keep data numeric for alignment
            st.table(display_df.style.format({
                'Commitment': '${:,.2f}',
                'Ownership %': '{:.2f}%'
            }))
            
        else:
            st.warning("No investors found.")

# === TAB 2: CAPITAL CALL (MAKER / CHECKER) ===
with tab2:
    st.header("Capital Call Management")
    call_tab1, call_tab2 = st.tabs(["1️⃣ Create Draft", "2️⃣ Review & Post"])
    
    # --- SUB-TAB 1: CREATE DRAFT ---
    with call_tab1:
        st.subheader("Step 1: Draft New Call")
        
        c1, c2 = st.columns(2)
        with c1:
            draft_amount = st.number_input("Total Call Amount ($)", value=100000.00, step=10000.00)
        with c2:
            draft_date = st.date_input("Due Date")
            
        if supabase:
            comm_resp = supabase.table('commitments').select("*, investors(display_name)").execute()
            if comm_resp.data:
                df_draft = pd.DataFrame(comm_resp.data)
                df_draft['Investor'] = df_draft['investors'].apply(lambda x: x['display_name'])
                
                total_comm = df_draft['committed_amount'].sum()
                # Calculate Share (Keep as Float)
                df_draft['Share'] = (df_draft['committed_amount'] / total_comm) * draft_amount
                
                # Preview
                st.markdown("### Allocation Preview")
                preview_df = df_draft[['Investor', 'Share']].copy()
                preview_df.index = preview_df.index + 1
                
                # THE FIX: Format as Currency
                st.table(preview_df.style.format({'Share': '${:,.2f}'}))
                
                if st.button("💾 Save as Draft", type="primary"):
                    try:
                        batch_data = {"batch_date": str(draft_date), "description": f"Call: {fmt(draft_amount)}", "status": "DRAFT"}
                        b_resp = supabase.table('batches').insert(batch_data).execute()
                        new_batch_id = b_resp.data[0]['id']
                        
                        entries = []
                        for idx, row in df_draft.iterrows():
                            entries.append({
                                "batch_id": new_batch_id,
                                "commitment_id": row['id'],
                                "trans_code": "CC-PRIN",
                                "amount": row['Share']
                            })
                        supabase.table('ledger_entries').insert(entries).execute()
                        st.success("✅ Draft Saved! Go to 'Review & Post' tab.")
                    except Exception as e:
                        st.error(str(e))
    
    # --- SUB-TAB 2: REVIEW & POST ---
    with call_tab2:
        st.subheader("Step 2: Review & Post")
        
        if supabase:
            draft_batches = supabase.table('batches').select("*").eq('status', 'DRAFT').execute()
            
            if draft_batches.data:
                batch_options = {f"{b['description']} ({b['batch_date']})": b['id'] for b in draft_batches.data}
                selected_desc = st.selectbox("Select Draft:", list(batch_options.keys()))
                selected_batch_id = batch_options[selected_desc]
                
                st.divider()
                st.markdown(f"**Reviewing:** {selected_desc}")
                
                draft_entries = supabase.table('ledger_entries').select("*, commitments(investors(display_name))").eq('batch_id', selected_batch_id).execute()
                
                if draft_entries.data:
                    df_review = pd.DataFrame(draft_entries.data)
                    df_review['Investor'] = df_review['commitments'].apply(lambda x: x['investors']['display_name'] if x and x['investors'] else "Unknown")
                    
                    # Ensure amount is float
                    df_review['amount'] = df_review['amount'].astype(float)
                    
                    disp_review = df_review[['Investor', 'amount']].copy()
                    disp_review.index = disp_review.index + 1
                    
                    # THE FIX: Format currency
                    st.table(disp_review.style.format({'amount': '${:,.2f}'}))
                    
                    col_p1, col_p2 = st.columns([1, 4])
                    with col_p1:
                        if st.button("🚀 POST TO LEDGER"):
                            supabase.table('batches').update({"status": "POSTED"}).eq('id', selected_batch_id).execute()
                            st.success("✅ Posted!")
                            st.rerun()
                    with col_p2:
                        if st.button("🗑️ DELETE DRAFT"):
                            supabase.table('ledger_entries').delete().eq('batch_id', selected_batch_id).execute()
                            supabase.table('batches').delete().eq('id', selected_batch_id).execute()
                            st.warning("Draft Deleted.")
                            st.rerun()
            else:
                st.info("No pending drafts.")

# === TAB 3: LIVE PCAP STATEMENT ===
with tab3:
    st.header("Partner Capital Account (Live)")
    st.markdown("View real-time ledger. **Note:** Only 'POSTED' transactions appear here.")
    
    if supabase:
        all_inv = supabase.table('investors').select("*").execute()
        inv_map = {i['display_name']: i['id'] for i in all_inv.data} if all_inv.data else {}
        
        if inv_map:
            sel_inv_name = st.selectbox("Select Investor:", list(inv_map.keys()))
            comm_res = supabase.table('commitments').select("id").eq('investor_id', inv_map[sel_inv_name]).execute()
            
            if comm_res.data:
                sel_comm_id = comm_res.data[0]['id']
                
                # Query Posted Only
                ledger_res = supabase.table('ledger_entries').select("*, batches!inner(status, batch_date)").eq('commitment_id', sel_comm_id).execute()
                
                if ledger_res.data:
                    raw_df = pd.DataFrame(ledger_res.data)
                    raw_df['status'] = raw_df['batches'].apply(lambda x: x['status'])
                    raw_df['date'] = raw_df['batches'].apply(lambda x: x['batch_date'])
                    
                    posted_df = raw_df[raw_df['status'] == 'POSTED'].copy()
                    
                    if not posted_df.empty:
                        # Convert to float for math
                        posted_df['amount'] = posted_df['amount'].astype(float)
                        
                        contrib = posted_df[posted_df['trans_code'] == 'CC-PRIN']['amount'].sum()
                        end_bal = contrib 
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Beginning Balance", "$0.00")
                        m2.metric("Contributions", fmt(contrib))
                        m3.metric("Ending Capital", fmt(end_bal))
                        
                        st.subheader("Transaction History")
                        hist_df = posted_df[['date', 'trans_code', 'amount']].copy()
                        hist_df.columns = ["Date", "Type", "Amount"]
                        hist_df.index = hist_df.index + 1
                        
                        # THE FIX: Format Currency
                        st.table(hist_df.style.format({'Amount': '${:,.2f}'}))
                        
                        st.divider()
                        pdf_bytes = create_pdf(sel_inv_name, "Harbor View Fund I", end_bal, posted_df)
                        st.download_button("📥 Download Statement (PDF)", pdf_bytes, "statement.pdf", "application/pdf")
                    else:
                        st.info("No posted transactions yet.")
                else:
                    st.info("No activity found.")
            else:
                st.warning("No commitment found for this investor.")
