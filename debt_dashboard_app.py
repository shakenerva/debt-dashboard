import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Debt & Savings Dashboard", page_icon="💶", layout="wide")

# -------------------------
# Simulation Function
# -------------------------
def simulate(loans_df, base_income, expenses, savings_split=0.5, months=120, start_date="2025-10-01",
             income_change_month=None, new_income=None):
    loans = loans_df.to_dict(orient="records")
    savings = 0.0
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")

    results = []
    for month in range(1, months+1):
        loans = [l for l in loans if l["Balance (€)"] > 0.01]
        total_start = sum(l["Balance (€)"] for l in loans)

        if total_start <= 0:
            break

        # Adjust income if job change month is reached
        current_income = base_income
        if income_change_month and new_income:
            if month >= income_change_month:
                current_income = new_income

        # Step 1: pay minimums
        for l in loans:
            pay = min(l["Min Payment (€)"], l["Balance (€)"])
            l["Balance (€)"] -= pay

        # Step 2: calculate leftover
        mandatory = sum(d["Min Payment (€)"] for d in loans)
        leftover = max(0, current_income - expenses - mandatory)

        # Step 3: split leftover into debt vs savings
        extra_debt = leftover * (1 - savings_split)
        extra_savings = leftover * savings_split

        # Apply extra to smallest debt
        if extra_debt > 0 and loans:
            loans.sort(key=lambda x: x["Balance (€)"])
            pay = min(extra_debt, loans[0]["Balance (€)"])
            loans[0]["Balance (€)"] -= pay

        # Grow savings
        savings += extra_savings

        total_end = sum(l["Balance (€)"] for l in loans)
        month_date = (start_dt + pd.DateOffset(months=month-1)).strftime("%b %Y")
        results.append({
            "Month": month,
            "Date": month_date,
            "Debt Start (€)": round(total_start,2),
            "Debt End (€)": round(total_end,2),
            "Savings (€)": round(savings,2),
            "Net Position (€)": round(savings - total_end,2),
            "Income Used (€)": current_income
        })

    return pd.DataFrame(results) if results else pd.DataFrame([{
        "Month": 0, "Date": start_date,
        "Debt Start (€)": 0, "Debt End (€)": 0,
        "Savings (€)": 0, "Net Position (€)": 0,
        "Income Used (€)": base_income
    }])

# -------------------------
# Sidebar Settings
# -------------------------
st.sidebar.title("⚙️ Settings")

income = st.sidebar.number_input("Current Monthly Income (€)", min_value=0, value=1800, step=50)
rent = st.sidebar.number_input("Rent (€)", min_value=0, value=750, step=10)
food_bills = st.sidebar.number_input("Food & Bills (€)", min_value=0, value=450, step=10)
other_exp = st.sidebar.number_input("Other Expenses (€)", min_value=0, value=0, step=10)
expenses = rent + food_bills + other_exp

st.sidebar.markdown("### 💼 Future Job Change")
job_change = st.sidebar.checkbox("Simulate future income change?")
income_change_month, new_income = None, None
if job_change:
    income_change_month = st.sidebar.number_input("Month of change (e.g. 12 = after 1 year)", min_value=1, value=12)
    new_income = st.sidebar.number_input("New Monthly Income (€)", min_value=0, value=2200, step=50)

st.sidebar.markdown("---")
strategy = st.sidebar.selectbox("Strategy", ["Safety First (all savings)", "Aggressive (all debt)", "Balanced 50/50", "Custom %"])
custom_split = st.sidebar.slider("Custom: % to savings", 0.0, 1.0, 0.5, 0.05)

if strategy == "Safety First (all savings)":
    savings_split = 1.0
elif strategy == "Aggressive (all debt)":
    savings_split = 0.0
elif strategy == "Balanced 50/50":
    savings_split = 0.5
else:
    savings_split = custom_split

months = st.sidebar.slider("Months to simulate", 12, 180, 120, 6)

# -------------------------
# Loan Input (Mobile-Friendly)
# -------------------------
st.title("💶 Debt & Savings Dashboard (v8 - Mobile Friendly)")
st.caption("Start date: Oct 2025. Add your loans manually using the form below.")

if "loans_df" not in st.session_state:
    st.session_state.loans_df = pd.DataFrame(columns=["Name", "Balance (€)", "APR %", "Min Payment (€)"])

st.subheader("➕ Add Loan")
with st.form("add_loan_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Loan Name")
        balance = st.number_input("Balance (€)", min_value=0.0, value=0.0, step=10.0)
    with col2:
        apr = st.number_input("APR %", min_value=0.0, value=0.0, step=0.1)
        minpay = st.number_input("Min Payment (€)", min_value=0.0, value=0.0, step=1.0)
    submitted = st.form_submit_button("Add Loan")
    if submitted and name and balance > 0 and minpay > 0:
        new_row = {"Name": name, "Balance (€)": balance, "APR %": apr, "Min Payment (€)": minpay}
        st.session_state.loans_df = pd.concat([st.session_state.loans_df, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"Loan '{name}' added!")

# Display current loans
if not st.session_state.loans_df.empty:
    st.subheader("📋 Current Loans")
    st.dataframe(st.session_state.loans_df, use_container_width=True)

# -------------------------
# Run Simulation
# -------------------------
if not st.session_state.loans_df.empty:
    df = simulate(st.session_state.loans_df, income, expenses, savings_split=savings_split, months=months,
                  start_date="2025-10-01", income_change_month=income_change_month, new_income=new_income)

    st.subheader("📅 Monthly Plan")
    st.dataframe(df, use_container_width=True, height=420)

    debt_free_months = int(df["Month"].iloc[-1])
    debt_free_date = df["Date"].iloc[-1]
    st.metric("Debt-Free", f"{debt_free_date} ({debt_free_months} months)")

    st.subheader("📈 Progress Over Time")
    chart_df = df.set_index("Date")[["Debt End (€)", "Savings (€)", "Net Position (€)"]]
    st.line_chart(chart_df, use_container_width=True)

    st.download_button("⬇️ Download Full Schedule (CSV)", data=df.to_csv(index=False),
                       file_name="debt_savings_plan.csv", mime="text/csv")
else:
    st.warning("Please add at least one loan to start the simulation.")
