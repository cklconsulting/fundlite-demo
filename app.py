import streamlit as st
import pandas as pd
import altair as alt

# --- PAGE CONFIGURATION (Browser Tab Title & Icon) ---
st.set_page_config(
    page_title="FundLite | Investor Portal",
    page_icon="📊",
    layout="wide"
)

# --- SESSION STATE (To remember inputs across tabs) ---
if 'fund_size' not in st.session_state:
    st.session_state.fund_size = 50000000
if 'commitments' not in st.session_state:
    st.session_state.commitments = 1000000

# --- SIDEBAR (Global Controls) ---
with st.sidebar:
    st.title("FundLite Admin")
    st.info("🔒 Secure Demo Environment")
    
    st.markdown("### Current User")
    st.text("Role: GP / Controller")
    st.text("Entity: Fund II, LP")
    
    st.divider()
    st.write("Development Status: **Alpha v0.1**")
    st.write("Built with Python & Streamlit")

# --- MAIN APP TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Fund Setup", "💸 Waterfall Engine", "📱 Investor Dashboard (Mock)"])

# === TAB 1: FUND SETUP ===
with tab1:
    st.header("Fund Configuration")
    st.markdown("Define the structural parameters for the fund. This drives the math in the backend.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Structure")
        fund_name = st.text_input("Fund Legal Name", value="Harbor View Real Estate Fund II, LP")
        inception_date = st.date_input("Inception Date")
        currency = st.selectbox("Base Currency", ["USD", "EUR", "GBP"])
        
    with col2:
        st.subheader("Economics")
        st.session_state.fund_size = st.number_input("Target Fund Size ($)", value=50000000, step=1000000)
        mgmt_fee = st.number_input("Management Fee (%)", value=2.0, step=0.1)
        hurdle_rate = st.number_input("Preferred Return / Hurdle (%)", value=8.0, step=0.5)

    st.success("✅ Configuration Saved to Memory")

# === TAB 2: WATERFALL ENGINE ===
with tab2:
    st.header("Distribution Waterfall Calculator")
    st.markdown("Simulate a Deal-by-Deal (American) distribution event.")
    
    # Inputs for the calculator
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        capital_contrib = st.number_input("Cap Contributed to Deal ($)", value=1000000)
    with lc2:
        accrued_pref = st.number_input("Accrued Pref ($)", value=150000)
    with lc3:
        catchup_pct = st.slider("GP Catch-up %", 0.0, 1.0, 0.20)
        
    st.divider()
    
    cash_to_dist = st.number_input("Cash Available for Distribution ($)", value=2500000, step=10000)
    
    if st.button("Run Waterfall Calculation", type="primary"):
        # --- THE LOGIC ENGINE ---
        log = []
        remaining = cash_to_dist
        
        # 1. Return of Capital
        b1 = min(remaining, capital_contrib)
        remaining -= b1
        
        # 2. Pref
        b2 = min(remaining, accrued_pref)
        remaining -= b2
        
        # 3. Catchup
        catchup_req = (b2 / (1 - catchup_pct)) * catchup_pct
        b3 = min(remaining, catchup_req)
        remaining -= b3
        
        # 4. Carry Split
        b4_lp = remaining * (1 - catchup_pct)
        b4_gp = remaining * catchup_pct
        
        # Totals
        total_lp = b1 + b2 + b4_lp
        total_gp = b3 + b4_gp
        
        # Display Results
        st.markdown("### 📊 Distribution Results")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total to LPs", f"${total_lp:,.2f}", delta="Net Distribution")
        m2.metric("Total to GP (Carry)", f"${total_gp:,.2f}", delta="Performance Fee")
        m3.metric("Effective Split", f"{round((total_gp/cash_to_dist)*100, 1)}% GP / {round((total_lp/cash_to_dist)*100, 1)}% LP")
        
        # Data Table
        breakdown_data = {
            "Bucket": ["1. Return of Capital", "2. Preferred Return", "3. GP Catch-up", "4. Carried Interest (GP)", "4. Residual (LP)"],
            "Amount": [b1, b2, b3, b4_gp, b4_lp],
            "Recipient": ["LP", "LP", "GP", "GP", "LP"]
        }
        df = pd.DataFrame(breakdown_data)
        st.table(df)

# === TAB 3: INVESTOR DASHBOARD ===
with tab3:
    st.header("Investor Portal View")
    st.markdown("*This is what the Limited Partner (LP) sees on their phone.*")
    
    # Mock Data for Visuals
    st.markdown("#### 👋 Welcome back, John Doe Trust")
    
    # KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("NAV", "$1,245,000", "+$45k")
    k2.metric("Net IRR", "14.2%", "+0.5%")
    k3.metric("TVPI", "1.45x")
    k4.metric("DPI", "0.32x")
    
    st.divider()
    
    # Chart
    st.subheader("Portfolio Value Over Time")
    chart_data = pd.DataFrame({
        'Date': pd.date_range(start='1/1/2023', periods=12, freq='M'),
        'Value': [1000000, 1020000, 1015000, 1050000, 1080000, 1100000, 1150000, 1140000, 1180000, 1200000, 1220000, 1245000]
    })
    
    c = alt.Chart(chart_data).mark_area(
        line={'color':'#4F46E5'},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='#4F46E5', offset=0),
                   alt.GradientStop(color='white', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x='Date',
        y='Value'
    ).properties(height=300)
    
    st.altair_chart(c, use_container_width=True)
