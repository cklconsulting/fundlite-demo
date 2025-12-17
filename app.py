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
    return f"${val:,.2f}"

def create_pdf(investor_name, fund_name, balance, unfunded, transactions):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, txt=fund_name, ln=True, align='C')
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 10, txt="Partner Capital Account Statement", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    
    # Info
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt=f"Investor: {investor_name}", ln=True)
    pdf.cell(0, 10, txt=f"Date: {date.today()}", ln=True)
    
    # Summary Box
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, txt=f"Ending Capital Balance: {fmt(balance)}", ln=True, fill=True)
    pdf.cell(0, 10, txt=f"Remaining Unfunded Commitment: {fmt(unfunded)}", ln=True, fill=True)
    
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
        # Simple Logic to clean up Description
        if "Call" in str(row['trans_code']): desc = "Capital Call"
        elif "DIST" in str(row['trans_code']): desc = "Distribution"
        else: desc = "P&L Allocation"
        
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
# UPDATED: Added Tab 5 for Distributions
tab1, tab2, tab4, tab5, tab3 = st.tabs(["📊 Fund Overview", "📢 Capital Calls", "📈 P&L Allocation", "💸 Distributions", "📄 Live PCAP Statement"])

# === TAB 1: OVERVIEW ===
with tab1:
    st.header("Fund Overview")
    if supabase:
        comm_data = supabase.table('commitments').select("*, investors(display_name)").execute()
        if comm_data.data:
            df = pd.DataFrame(comm_data.data)
            df['Investor Name'] = df['investors'].apply(lambda x: x['display_name'] if x else "Unknown")
            df['Commitment'] = df['committed_amount']
            
            total_fund = df['Commitment'].sum()
            df['Ownership %'] = (df['Commitment'] / total_fund) * 100
            
            c1, c2 = st.columns(2)
            c1.metric("Total Fund Size", fmt(total_fund))
            c2.metric("Total Investors", len(df))
            
            st.divider()
            st.subheader("Cap Table (Ownership)")
            
            display_df = df[['Investor Name', 'Commitment', 'Ownership %']].copy()
            display_df.index = display_df.index + 1
            st.table(display_df.style.format({'Commitment': '${:,.2f}', 'Ownership %': '{:.2f}%'}))
        else:
            st.warning("No investors found.")

# === TAB 2: CAPITAL CALL ===
with tab2:
    st.header("Capital Call Management")
    call_tab1, call_tab2 = st.tabs(["1️⃣ Create Draft", "2️⃣ Review & Post"])
    
    with call_tab1:
        st.subheader("Step 1: Draft New Call")
        c1, c2 = st.columns(2)
        with c1:
            draft_amount = st.number_input("Total Call Amount ($)", value=100000.00, step=10000.00)
        with c2:
            draft_date = st.date_input("Due Date")
            
        if supabase:
            if st.button("Calculate Split"):
                comm_resp = supabase.table('commitments').select("*, investors(display_name)").execute()
                if comm_resp.data:
                    df_draft = pd.DataFrame(comm_resp.data)
                    df_draft['Investor'] = df_draft['investors'].apply(lambda x: x['display_name'])
                    total_comm = df_draft['committed_amount'].sum()
                    df_draft['Share'] = (df_draft['committed_amount'] / total_comm) * draft_amount
                    
                    st.markdown("### Preview")
                    preview_df = df_draft[['Investor', 'Share']].copy()
                    preview_df.index = preview_df.index + 1
                    st.table(preview_df.style.format({'Share': '${:,.2f}'}))
                    st.session_state['last_cc_draft'] = df_draft

            if st.button("💾 Save Capital Call Draft", type="primary"):
                if 'last_cc_draft' in st.session_state:
                    try:
                        batch_data = {"batch_date": str(draft_date), "description": f"Call: {fmt(draft_amount)}", "status": "DRAFT"}
                        b_resp = supabase.table('batches').insert(batch_data).execute()
                        new_batch_id = b_resp.data[0]['id']
                        entries = []
                        for idx, row in st.session_state['last_cc_draft'].iterrows():
                            entries.append({"batch_id": new_batch_id, "commitment_id": row['id'], "trans_code": "CC-PRIN", "amount": row['Share']})
                        supabase.table('ledger_entries').insert(entries).execute()
                        st.success("✅ Draft Saved!")
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.error("Please calculate split first.")

    with call_tab2:
        st.subheader("Review & Post")
        if supabase:
            draft_batches = supabase.table('batches').select("*").eq('status', 'DRAFT').ilike('description', '%Call%').execute()
            if draft_batches.data:
                batch_options = {f"{b['description']} ({b['batch_date']})": b['id'] for b in draft_batches.data}
                sel_desc = st.selectbox("Select Call Draft:", list(batch_options.keys()))
                sel_id = batch_options[sel_desc]
                
                draft_entries = supabase.table('ledger_entries').select("*, commitments(investors(display_name))").eq('batch_id', sel_id).execute()
                if draft_entries.data:
                    df_rev = pd.DataFrame(draft_entries.data)
                    df_rev['Investor'] = df_rev['commitments'].apply(lambda x: x['investors']['display_name'])
                    df_rev['amount'] = df_rev['amount'].astype(float)
                    
                    disp = df_rev[['Investor', 'amount']].copy()
                    disp.index = disp.index + 1
                    st.table(disp.style.format({'amount': '${:,.2f}'}))
                    
                    if st.button("🚀 POST CALL"):
                        supabase.table('batches').update({"status": "POSTED"}).eq('id', sel_id).execute()
                        st.success("Posted!")
                        st.rerun()
            else:
                st.info("No pending drafts.")

# === TAB 4: P&L ALLOCATION ===
with tab4:
    st.header("P&L Allocation")
    pl_tab1, pl_tab2 = st.tabs(["1️⃣ Draft P&L", "2️⃣ Review & Post"])
    
    with pl_tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            pl_amount = st.number_input("Total Amount ($)", value=10000.00, step=500.00)
        with c2:
            type_map = {"Income (Ordinary)": "INC-ORD", "Expense (General)": "EXP-GEN", "Gain (Realized)": "GAIN-RL", "Loss (Realized)": "LOSS-RL"}
            pl_type = st.selectbox("Transaction Type", list(type_map.keys()))
            db_code = type_map[pl_type]
        with c3:
            pl_date = st.date_input("Trans. Date", key="pl_date")
        pl_desc = st.text_input("Description", "Q1 Fees")

        if supabase:
            if st.button("Preview P&L Split"):
                comm_resp = supabase.table('commitments').select("*, investors(display_name)").execute()
                if comm_resp.data:
                    df_pl = pd.DataFrame(comm_resp.data)
                    df_pl['Investor'] = df_pl['investors'].apply(lambda x: x['display_name'])
                    total_comm = df_pl['committed_amount'].sum()
                    df_pl['Share'] = (df_pl['committed_amount'] / total_comm) * pl_amount
                    st.markdown("### Allocation Preview")
                    preview_pl = df_pl[['Investor', 'Share']].copy()
                    preview_pl.index = preview_pl.index + 1
                    st.table(preview_pl.style.format({'Share': '${:,.2f}'}))
                    st.session_state['last_pl_draft'] = (df_pl, db_code)
            
            if st.button("💾 Save P&L Draft", type="primary"):
                if 'last_pl_draft' in st.session_state:
                    df_save, code_save = st.session_state['last_pl_draft']
                    try:
                        batch_data = {"batch_date": str(pl_date), "description": f"{pl_type}: {pl_desc}", "status": "DRAFT"}
                        b_resp = supabase.table('batches').insert(batch_data).execute()
                        new_batch_id = b_resp.data[0]['id']
                        entries = []
                        for idx, row in df_save.iterrows():
                            entries.append({"batch_id": new_batch_id, "commitment_id": row['id'], "trans_code": code_save, "amount": row['Share']})
                        supabase.table('ledger_entries').insert(entries).execute()
                        st.success("✅ P&L Draft Saved!")
                    except Exception as e:
                        st.error(str(e))

    with pl_tab2:
        st.subheader("Review P&L Drafts")
        if supabase:
            # Filter for P&L types (Batches that are NOT Call and NOT Distribution)
            draft_batches = supabase.table('batches').select("*").eq('status', 'DRAFT').not_.ilike('description', '%Call%').not_.ilike('description', '%Dist%').execute()
            if draft_batches.data:
                batch_options = {f"{b['description']} ({b['batch_date']})": b['id'] for b in draft_batches.data}
                sel_desc = st.selectbox("Select P&L Draft:", list(batch_options.keys()))
                sel_id = batch_options[sel_desc]
                
                draft_entries = supabase.table('ledger_entries').select("*, commitments(investors(display_name))").eq('batch_id', sel_id).execute()
                if draft_entries.data:
                    df_rev = pd.DataFrame(draft_entries.data)
                    df_rev['Investor'] = df_rev['commitments'].apply(lambda x: x['investors']['display_name'])
                    df_rev['amount'] = df_rev['amount'].astype(float)
                    
                    disp = df_rev[['Investor', 'trans_code', 'amount']].copy()
                    disp.index = disp.index + 1
                    st.table(disp.style.format({'amount': '${:,.2f}'}))
                    
                    c1, c2 = st.columns([1,4])
                    with c1:
                        if st.button("🚀 POST P&L"):
                            supabase.table('batches').update({"status": "POSTED"}).eq('id', sel_id).execute()
                            st.success("Posted!")
                            st.rerun()
                    with c2:
                        if st.button("🗑️ DELETE"):
                             supabase.table('ledger_entries').delete().eq('batch_id', sel_id).execute()
                             supabase.table('batches').delete().eq('id', sel_id).execute()
                             st.rerun()
            else:
                st.info("No pending P&L drafts.")

# === TAB 5: DISTRIBUTIONS (NEW!) ===
with tab5:
    st.header("Distributions (Cash Out)")
    st.markdown("Distribute cash to investors. Choose **Return of Capital** (ROC) or **Gain**.")
    
    dist_tab1, dist_tab2 = st.tabs(["1️⃣ Draft Distribution", "2️⃣ Review & Post"])
    
    with dist_tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            dist_amount = st.number_input("Total Distribution ($)", value=50000.00, step=5000.00)
        with c2:
            # Code map for distributions
            dist_map = {"Return of Capital": "DIST-ROC", "Realized Gain Dist": "DIST-GAIN"}
            dist_type = st.selectbox("Distribution Type", list(dist_map.keys()))
            dist_code = dist_map[dist_type]
        with c3:
            dist_date = st.date_input("Date", key="dist_date")
            
        if supabase:
            if st.button("Preview Distribution"):
                comm_resp = supabase.table('commitments').select("*, investors(display_name)").execute()
                if comm_resp.data:
                    df_dist = pd.DataFrame(comm_resp.data)
                    df_dist['Investor'] = df_dist['investors'].apply(lambda x: x['display_name'])
                    total_comm = df_dist['committed_amount'].sum()
                    
                    # Pro-rata Split
                    df_dist['Share'] = (df_dist['committed_amount'] / total_comm) * dist_amount
                    
                    st.markdown("### Allocation Preview")
                    preview_dist = df_dist[['Investor', 'Share']].copy()
                    preview_dist.index = preview_dist.index + 1
                    st.table(preview_dist.style.format({'Share': '${:,.2f}'}))
                    
                    st.session_state['last_dist_draft'] = (df_dist, dist_code)
            
            if st.button("💾 Save Distribution Draft", type="primary"):
                if 'last_dist_draft' in st.session_state:
                    df_save, code_save = st.session_state['last_dist_draft']
                    try:
                        batch_data = {
                            "batch_date": str(dist_date), 
                            "description": f"Dist ({dist_type}): {fmt(dist_amount)}", 
                            "status": "DRAFT"
                        }
                        b_resp = supabase.table('batches').insert(batch_data).execute()
                        new_batch_id = b_resp.data[0]['id']
                        
                        entries = []
                        for idx, row in df_save.iterrows():
                            entries.append({
                                "batch_id": new_batch_id, 
                                "commitment_id": row['id'], 
                                "trans_code": code_save, 
                                "amount": row['Share']
                            })
                        supabase.table('ledger_entries').insert(entries).execute()
                        st.success("✅ Distribution Draft Saved!")
                    except Exception as e:
                        st.error(str(e))

    with dist_tab2:
        st.subheader("Review Distribution Drafts")
        if supabase:
            # Filter for Distributions only
            draft_batches = supabase.table('batches').select("*").eq('status', 'DRAFT').ilike('description', '%Dist%').execute()
            
            if draft_batches.data:
                batch_options = {f"{b['description']} ({b['batch_date']})": b['id'] for b in draft_batches.data}
                sel_desc = st.selectbox("Select Dist Draft:", list(batch_options.keys()))
                sel_id = batch_options[sel_desc]
                
                draft_entries = supabase.table('ledger_entries').select("*, commitments(investors(display_name))").eq('batch_id', sel_id).execute()
                if draft_entries.data:
                    df_rev = pd.DataFrame(draft_entries.data)
                    df_rev['Investor'] = df_rev['commitments'].apply(lambda x: x['investors']['display_name'])
                    df_rev['amount'] = df_rev['amount'].astype(float)
                    
                    disp = df_rev[['Investor', 'trans_code', 'amount']].copy()
                    disp.index = disp.index + 1
                    st.table(disp.style.format({'amount': '${:,.2f}'}))
                    
                    c1, c2 = st.columns([1,4])
                    with c1:
                        if st.button("🚀 POST DISTRIBUTION"):
                            supabase.table('batches').update({"status": "POSTED"}).eq('id', sel_id).execute()
                            st.success("Posted!")
                            st.rerun()
                    with c2:
                        if st.button("🗑️ DELETE"):
                             supabase.table('ledger_entries').delete().eq('batch_id', sel_id).execute()
                             supabase.table('batches').delete().eq('id', sel_id).execute()
                             st.rerun()
            else:
                st.info("No pending Distribution drafts.")

# === TAB 3: LIVE PCAP STATEMENT (FINAL) ===
with tab3:
    st.header("Partner Capital Account (Live)")
    st.markdown("Real-time view. **Note:** Distributions decrease Ending Capital.")
    
    if supabase:
        all_inv = supabase.table('investors').select("*").execute()
        inv_map = {i['display_name']: i['id'] for i in all_inv.data} if all_inv.data else {}
        
        if inv_map:
            sel_inv_name = st.selectbox("Select Investor:", list(inv_map.keys()))
            comm_res = supabase.table('commitments').select("*").eq('investor_id', inv_map[sel_inv_name]).execute()
            
            if comm_res.data:
                sel_comm_id = comm_res.data[0]['id']
                total_commitment = float(comm_res.data[0]['committed_amount'])
                
                # Query Posted Transactions
                ledger_res = supabase.table('ledger_entries').select("*, batches!inner(status, batch_date)").eq('commitment_id', sel_comm_id).execute()
                
                if ledger_res.data:
                    raw_df = pd.DataFrame(ledger_res.data)
                    raw_df['status'] = raw_df['batches'].apply(lambda x: x['status'])
                    raw_df['date'] = raw_df['batches'].apply(lambda x: x['batch_date'])
                    
                    posted_df = raw_df[raw_df['status'] == 'POSTED'].copy()
                    
                    if not posted_df.empty:
                        posted_df['amount'] = posted_df['amount'].astype(float)
                        
                        # --- ACCOUNTING LOGIC ---
                        contributions = posted_df[posted_df['trans_code'] == 'CC-PRIN']['amount'].sum()
                        additions = posted_df[posted_df['trans_code'].isin(['INC-ORD', 'GAIN-RL'])]['amount'].sum()
                        deductions = posted_df[posted_df['trans_code'].isin(['EXP-GEN', 'LOSS-RL'])]['amount'].sum()
                        
                        # Distributions (Both ROC and Gain decrease the capital account)
                        distributions = posted_df[posted_df['trans_code'].isin(['DIST-ROC', 'DIST-GAIN'])]['amount'].sum()
                        
                        # Calculations
                        ending_balance = contributions + additions - deductions - distributions
                        unfunded_balance = total_commitment - contributions
                        
                        # Metrics
                        m1, m2, m3, m4, m5 = st.columns(5)
                        
                        m1.metric("Total Commitment", fmt(total_commitment))
                        m2.metric("Unfunded Balance", fmt(unfunded_balance)) 
                        m3.metric("Total Distributed", fmt(distributions))
                        m4.metric("Net Income (P&L)", fmt(additions - deductions))
                        m5.metric("Ending Capital", fmt(ending_balance))
                        
                        st.divider()
                        st.subheader("Transaction History")
                        hist_df = posted_df[['date', 'trans_code', 'amount']].copy()
                        hist_df.columns = ["Date", "Type", "Amount"]
                        hist_df.index = hist_df.index + 1
                        
                        # Color coding: Expenses AND Distributions are negative logic
                        def format_accounting(row):
                            val = row['Amount']
                            code = row['Type']
                            if code in ['EXP-GEN', 'LOSS-RL', 'DIST-ROC', 'DIST-GAIN']:
                                return f"({fmt(val)})"
                            return fmt(val)

                        hist_df['Display Amount'] = hist_df.apply(format_accounting, axis=1)
                        st.table(hist_df[['Date', 'Type', 'Display Amount']].style.set_properties(
                            subset=['Display Amount'], **{'text-align': 'right'}
                        ))
                        
                        st.divider()
                        pdf_bytes = create_pdf(sel_inv_name, "Harbor View Fund I", ending_balance, unfunded_balance, posted_df)
                        st.download_button("📥 Download Official Statement", pdf_bytes, "statement.pdf", "application/pdf")
                    else:
                        st.info("No posted transactions yet.")
                else:
                    st.info("No activity found.")
            else:
                st.warning("No commitment found.")
