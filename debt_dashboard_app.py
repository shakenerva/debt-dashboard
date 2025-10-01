import pandas as pd
import streamlit as st
from datetime import datetime

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="Debt & Savings Dashboard", page_icon="💶", layout="wide")

# -------------------------
# Default loans
# -------------------------
def load_default_loans():
    data = [
        {"Name": "Card 1 (Ethn Bank)", "Balance (€)": 2108.28, "APR %": 0.0, "Min Payment (€)": 45},
        {"Name": "Card 2 (Alph Bank)", "Balance (€)": 1531.16, "APR %": 0.0, "Min Payment (€)": 24},
        {"Name": "Car Loan (Alpha Bank)", "Balance (€)": 3191.32, "APR %": 0.0, "Min Payment (€)": 69},
        {"Name": "Loan_no2 (Alpha Bank)", "Balance (€)": 206.00, "APR %": 0.0, "Min Payment (€)": 27},
        {"Name": "Loan_no3 (Alpha Bank)", "Balance (€)": 555.97, "APR %": 0.0, "Min Payment (€)": 30},
        {"Name": "Loan_no4 (Alpha TFI)", "Balance (€)": 642.47, "APR %": 0.0, "Min Payment (€)": 15},
    ]
    return pd.DataFrame(data)

# -------------------------
# Simulation
# -------------------------
def simulate(loans_df, base_income, expenses, savings_split=0.5, months=120, 
             start_date="2025-10-01", income_change_month=None, new_income=None):
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

    # Ensure DataFrame is never empty
    if not results:
        return pd.DataFrame([{
            "Month": 0,
            "Date": start_date,
            "Debt Start (€)": 0,
            "Debt End (€)": 0,
            "Savings (€)": 0,
            "Net Position (€)": 0,
            "Income Used (€)": base_income
        }])

    return pd.DataFrame(results)

# -------------------------
# Sidebar
# -------------------------
st.sidebar.title("⚙️ Settings")

# Income & expenses
income = st.sidebar.number_input("Current Monthly Income (€)", min_value=0, value=1800, step=50)
rent = st.sidebar.number_input("Rent (€)", min_value=0, value=750, step=10)
food_bills = st.sidebar.number_input("Food & Bills (€)", min_value=0, value=450, step=10)
other_exp = st.sidebar.number_input("Other Expenses (€)", min_value=0, value=0, step=10)
expenses = rent + food_bills + other_exp

# Future job change
st.sidebar.markdown("### 💼 Future Job Change")
job_change = st.sidebar.checkbox("Simulate future income change?")
income_change_month = None
new_income = None
if job_change:
    income_change_month = st.sidebar.number_input("Month of change (e.g. 12 = after 1 year)", min_value=1, value=12)
    new_income = st.sidebar.number_input("New Monthly Income (€)", min_value=0, value=2200, step=50)

# Strategy
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

# Loans table
if "loans_df" not in st.session_state or st.session_state.loans_df.empty:
    st.session_state.loans_df = load_default_loans()
loans_df = st.data_editor(st.session_state.loans_df, num_rows="dynamic", use_container_width=True)
st.session_state.loans_df = loans_df

# -------------------------
# Main
# -------------------------
st.title("💶 Debt & Savings Dashboard for Herve")
st.caption("Start date: Oct 2025. Supports future job income changes.")

# Run simulation
df = simulate(loans_df, income, expenses, savings_split=savings_split, months=months,
              start_date="2025-10-01", income_change_month=income_change_month, new_income=new_income)

st.subheader("📅 Monthly Plan")
st.dataframe(df, use_container_width=True, height=420)

if not df.empty:
    debt_free_months = int(df["Month"].iloc[-1])
    debt_free_date = df["Date"].iloc[-1]
    st.metric("Debt-Free", f"{debt_free_date} ({debt_free_months} months)")

st.subheader("📈 Progress Over Time")
chart_df = df.set_index("Date")[["Debt End (€)", "Savings (€)", "Net Position (€)"]]
st.line_chart(chart_df, use_container_width=True)

# Download option
st.download_button("⬇️ Download Full Schedule (CSV)", data=df.to_csv(index=False), file_name="debt_savings_plan.csv", mime="text/csv")
