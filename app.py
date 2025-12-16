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
        
            
            # --- THE FIX: Right-Align Numbers using Pandas Styler ---
            st.subheader("Cap Table (Ownership)")
            
            # 1. Start Index at 1
            display_df.index = display_df.index + 1
            
            # 2. Apply Right Alignment style
            # We tell it: "For columns 'Commitment' and 'Ownership %', align text to right"
            styled_df = display_df.style.set_properties(
                subset=['Commitment', 'Ownership %'], 
                **{'text-align': 'right'}
            )
            
            st.table(styled_df)            
            
        else:
            st.warning("No investors found. Go add some in Supabase!")

# === TAB 2: CAPITAL CALL (MAKER / CHECKER WORKFLOW) ===
with tab2:
    st.header("Capital Call Management")
    
    # Sub-tabs for the workflow
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
            # Fetch investors to preview the split
            comm_resp = supabase.table('commitments').select("*, investors(display_name)").execute()
            if comm_resp.data:
                df_draft = pd.DataFrame(comm_resp.data)
                df_draft['Investor'] = df_draft['investors'].apply(lambda x: x['display_name'])
                
                # Calculate
                total_comm = df_draft['committed_amount'].sum()
                df_draft['Share'] = (df_draft['committed_amount'] / total_comm) * draft_amount
                
                # DISPLAY PREVIEW
                st.markdown("### Allocation Preview")
                preview_df = df_draft[['Investor', 'Share']].copy()
                preview_df['Share'] = preview_df['Share'].apply(fmt)
                
                # FIX: Start Index at 1
                preview_df.index = preview_df.index + 1
                st.table(preview_df)
                
                if st.button("💾 Save as Draft", type="primary"):
                    try:
                        # A. Create Batch (Status = DRAFT)
                        batch_data = {
                            "batch_date": str(draft_date),
                            "description": f"Call: {fmt(draft_amount)}",
                            "status": "DRAFT" # <--- KEY CHANGE
                        }
                        b_resp = supabase.table('batches').insert(batch_data).execute()
                        new_batch_id = b_resp.data[0]['id']
                        
                        # B. Insert Draft Entries
                        entries = []
                        for idx, row in df_draft.iterrows():
                            entries.append({
                                "batch_id": new_batch_id,
                                "commitment_id": row['id'],
                                "trans_code": "CC-PRIN",
                                "amount": row['Share']
                            })
                        supabase.table('ledger_entries').insert(entries).execute()
                        st.success("✅ Draft Saved! Go to 'Review & Post' tab to finalize.")
                        
                    except Exception as e:
                        st.error(str(e))
    
    # --- SUB-TAB 2: REVIEW & POST ---
    with call_tab2:
        st.subheader("Step 2: Review & Post")
        
        if supabase:
            # Fetch batches that are strictly 'DRAFT'
            draft_batches = supabase.table('batches').select("*").eq('status', 'DRAFT').execute()
            
            if draft_batches.data:
                # Let user select a batch to review
                batch_options = {f"{b['description']} ({b['batch_date']})": b['id'] for b in draft_batches.data}
                selected_desc = st.selectbox("Select Draft to Review:", list(batch_options.keys()))
                selected_batch_id = batch_options[selected_desc]
                
                st.divider()
                
                # Show the details of this draft
                st.markdown(f"**Reviewing:** {selected_desc}")
                
                # Fetch entries for this batch
                draft_entries = supabase.table('ledger_entries').select("*, commitments(investors(display_name))").eq('batch_id', selected_batch_id).execute()
                
                if draft_entries.data:
                    df_review = pd.DataFrame(draft_entries.data)
                    # Flatten the name again
                    df_review['Investor'] = df_review['commitments'].apply(lambda x: x['investors']['display_name'] if x and x['investors'] else "Unknown")
                    
                    # Display for Review
                    disp_review = df_review[['Investor', 'amount']].copy()
                    disp_review['amount'] = disp_review['amount'].apply(fmt)
                    
                    # FIX: Start Index at 1
                    disp_review.index = disp_review.index + 1
                    st.table(disp_review)
                    
                    # THE "POST" ACTION
                    col_p1, col_p2 = st.columns([1, 4])
                    with col_p1:
                        if st.button("🚀 POST TO LEDGER"):
                            # Update Batch Status to POSTED
                            supabase.table('batches').update({"status": "POSTED"}).eq('id', selected_batch_id).execute()
                            st.success("✅ Transaction Posted Successfully!")
                            st.rerun() # Refresh page
                    with col_p2:
                        if st.button("🗑️ DELETE DRAFT"):
                            # Delete entries first (Foreign Key constraint), then batch
                            supabase.table('ledger_entries').delete().eq('batch_id', selected_batch_id).execute()
                            supabase.table('batches').delete().eq('id', selected_batch_id).execute()
                            st.warning("Draft Deleted.")
                            st.rerun()
                            
            else:
                st.info("No pending drafts found.")

# === TAB 3: LIVE PCAP STATEMENT (ROBUST VERSION) ===
with tab3:
    st.header("Partner Capital Account (Live)")
    st.markdown("View real-time ledger. **Note:** Only 'POSTED' transactions appear here.")
    
    if supabase:
        # 1. Fetch Investors
        all_inv = supabase.table('investors').select("*").execute()
        inv_map = {i['display_name']: i['id'] for i in all_inv.data} if all_inv.data else {}
        
        if inv_map:
            sel_inv_name = st.selectbox("Select Investor:", list(inv_map.keys()))
            
            # Find the commitment ID for this investor
            # (In a real app, we'd handle multiple funds per investor, simplifying here)
            comm_res = supabase.table('commitments').select("id").eq('investor_id', inv_map[sel_inv_name]).execute()
            
            if comm_res.data:
                sel_comm_id = comm_res.data[0]['id']
                
                # 2. ROBUST QUERY: Join with Batches to filter for POSTED only
                # Supabase-py join syntax is: "*, batches!inner(*)"
                # This fetches entries AND their parent batch info
                ledger_res = supabase.table('ledger_entries').select("*, batches!inner(status, batch_date)").eq('commitment_id', sel_comm_id).execute()
                
                # Filter in Python for safety
                if ledger_res.data:
                    raw_df = pd.DataFrame(ledger_res.data)
                    
                    # Extract Batch Status
                    raw_df['status'] = raw_df['batches'].apply(lambda x: x['status'])
                    raw_df['date'] = raw_df['batches'].apply(lambda x: x['batch_date'])
                    
                    # FILTER: Keep ONLY 'POSTED'
                    posted_df = raw_df[raw_df['status'] == 'POSTED'].copy()
                    
                    if not posted_df.empty:
                        # Calc Totals
                        contrib = posted_df[posted_df['trans_code'] == 'CC-PRIN']['amount'].sum()
                        end_bal = contrib # - distributions (future)
                        
                        # Metrics
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Beginning Balance", "$0.00")
                        m2.metric("Contributions", fmt(contrib))
                        m3.metric("Ending Capital", fmt(end_bal))
                        
                        # Display History
                        st.subheader("Transaction History")
                        hist_df = posted_df[['date', 'trans_code', 'amount']].copy()
                        hist_df['amount'] = hist_df['amount'].apply(fmt)
                        hist_df.columns = ["Date", "Type", "Amount"]
                        
                        # FIX: Start Index at 1
                        hist_df.index = hist_df.index + 1
                        st.table(hist_df)
                        
                        # PDF Button Logic (Re-used from before)
                        st.divider()
                        pdf_bytes = create_pdf(sel_inv_name, "Harbor View Fund I", end_bal, posted_df)
                        st.download_button("📥 Download Statement (PDF)", pdf_bytes, "statement.pdf", "application/pdf")
                        
                    else:
                        st.info("No posted transactions yet (check Drafts?).")
                else:
                    st.info("No activity found.")
            else:
                st.warning("This investor has no commitment to the fund.")
