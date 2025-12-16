import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta

# --- HELPER: FORMATTING FUNCTION ---
def fmt(value):
    return f"${value:,.2f}"

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FundLite V2 | Investor Portal", page_icon="📊", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("FundLite Admin")
    st.info("🔒 Secure Demo Environment v2.0")
    
    # 1. Multi-Investor Simulation
    st.header("Simulation Settings")
    investor_profile = st.selectbox(
        "View as Investor Type:",
        ["Standard LP (Class A)", "Founder/VIP (Class B)"]
    )
    
    # Logic to change fees based on selection
    if investor_profile == "Standard LP (Class A)":
        mgmt_fee_rate = 2.0
        carry_rate = 0.20
        tag = "Fee Paying"
    else:
        mgmt_fee_rate = 0.0
        carry_rate = 0.10
        tag = "No Fee / Reduced Carry"
        
    st.caption(f"Applied Profile: **{tag}**")
    st.caption(f"Mgmt Fee: {mgmt_fee_rate}% | Carry: {int(carry_rate*100)}%")

# --- MAIN APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Fund Setup", "💸 Smart Waterfall (Cumulative)", "📱 Investor Dashboard"])

# === TAB 1: FUND SETUP ===
with tab1:
    st.header("Fund Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Structure")
        fund_name = st.text_input("Fund Legal Name", value="Harbor View Real Estate Fund II, LP")
        inception_date = st.date_input("Inception Date", value=date(2023, 1, 1))
        
    with col2:
        st.subheader("Economics (Global)")
        fund_size = st.number_input("Target Fund Size ($)", value=50000000.00, step=1000000.00, format="%.2f")
        hurdle_rate = st.number_input("Preferred Return (%)", value=8.0, step=0.5)

# === TAB 2: WATERFALL ENGINE ===
with tab2:
    st.header("Deal-by-Deal Distribution Engine")
    st.markdown("Calculates **Time-Weighted** Preferred Return based on dates.")
    
    # --- STEP 1: INPUTS ---
    st.subheader("1. Deal Context")
    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        capital_contrib = st.number_input("Capital Contributed ($)", value=1000000.00, step=10000.00)
    with wc2:
        # Date Logic for Pref
        last_dist_date = st.date_input("Last Distribution Date", value=date(2023, 1, 1))
        current_dist_date = st.date_input("Current Distribution Date", value=date(2024, 1, 1))
    with wc3:
        # Calculate Days
        days_elapsed = (current_dist_date - last_dist_date).days
        st.metric("Days Elapsed", f"{days_elapsed} days")
    
    # --- STEP 2: PREF CALCULATION ---
    # Formula: Principal * Rate * (Days / 365)
    calc_pref_amount = capital_contrib * (hurdle_rate / 100) * (days_elapsed / 365)
    
    st.info(f"🧮 **Auto-Calculated Pref:** {fmt(capital_contrib)} × {hurdle_rate}% × ({days_elapsed}/365) = **{fmt(calc_pref_amount)}**")
    
    # Allows user to override if needed (e.g. cumulative unpaid from prior periods)
    accrued_pref = st.number_input("Total Accrued Pref Output (Editable)", value=calc_pref_amount, step=1000.00)

    st.divider()
    
    # --- STEP 3: DISTRIBUTION ---
    st.subheader("2. Execute Distribution")
    cash_to_dist = st.number_input("Cash Available to Distribute ($)", value=2500000.00, step=10000.00)
    
    if st.button("Run Waterfall Calculation", type="primary"):
        remaining = cash_to_dist
        
        # Bucket 1: Return of Capital
        b1 = min(remaining, capital_contrib)
        remaining -= b1
        
        # Bucket 2: Pref (Time-Weighted)
        b2 = min(remaining, accrued_pref)
        remaining -= b2
        
        # Bucket 3: Catchup (Dynamic based on selected Class)
        catchup_req = (b2 / (1 - carry_rate)) * carry_rate
        b3 = min(remaining, catchup_req)
        remaining -= b3
        
        # Bucket 4: Carry Split
        b4_lp = remaining * (1 - carry_rate)
        b4_gp = remaining * carry_rate
        
        # Totals
        total_lp = b1 + b2 + b4_lp
        total_gp = b3 + b4_gp
        
        # Display Results
        st.markdown("### 📊 Distribution Results")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total to LP", fmt(total_lp), delta=f"Split: {round((total_lp/cash_to_dist)*100, 1)}%")
        m2.metric("Total to GP (Carry)", fmt(total_gp), delta=f"Split: {round((total_gp/cash_to_dist)*100, 1)}%")
        m3.metric("GP Carry Rate Used", f"{int(carry_rate*100)}%")
        
        # Detailed Table
        breakdown_data = {
            "Waterfall Bucket": ["1. Return of Capital", "2. Preferred Return (Time-Weighted)", "3. GP Catch-up", "4. Carried Interest (GP)", "4. Residual (LP)"],
            "Amount": [fmt(b1), fmt(b2), fmt(b3), fmt(b4_gp), fmt(b4_lp)],
            "Recipient": ["LP", "LP", "GP", "GP", "LP"]
        }
        st.table(pd.DataFrame(breakdown_data))

# === TAB 3: INVESTOR DASHBOARD ===
with tab3:
    st.header(f"Investor Portal: {investor_profile}")
    st.markdown("*Real-time view of current position.*")
    
    # MOCK DATA based on profile
    if investor_profile == "Standard LP (Class A)":
        committed = 5000000.00
        funded = 2500000.00
        nav = 2850000.00
    else:
        # Founder put in less money but has higher returns due to no fees
        committed = 1000000.00
        funded = 500000.00
        nav = 600000.00 # Higher relative NAV due to 0% fees
        
    unfunded = committed - funded
    
    # --- ROW 1: CAPITAL STATUS (The new Request) ---
    st.subheader("Capital Account Status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Committed", fmt(committed))
    c2.metric("Total Funded", fmt(funded), delta=f"{int(funded/committed*100)}% Called")
    c3.metric("Remaining Unfunded", fmt(unfunded))
    
    st.divider()
    
    # --- ROW 2: PERFORMANCE ---
    st.subheader("Performance Metrics")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current NAV", fmt(nav))
    k2.metric("Net IRR", "14.2%")
    k3.metric("TVPI", "1.45x")
    k4.metric("DPI", "0.32x")
    
    # Chart
    st.subheader("NAV Growth")
    chart_data = pd.DataFrame({
        'Date': pd.date_range(start='1/1/2023', periods=6, freq='Q'),
        'Value': [funded * 0.98, funded * 1.05, funded * 1.10, funded * 1.12, funded * 1.15, nav]
    })
    
    c = alt.Chart(chart_data).mark_area(
        line={'color':'#10B981'},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='#10B981', offset=0),
                   alt.GradientStop(color='white', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(x='Date', y='Value').properties(height=300)
    
    st.altair_chart(c, use_container_width=True)
