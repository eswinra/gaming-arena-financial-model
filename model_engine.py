"""
MODULE 2: 3-STATEMENT MODEL ENGINE
=====================================
Gaming Arena, LLC — Linked Financial Statements in Python

WHAT THIS FILE TEACHES YOU:
- pandas DataFrames (the core tool for financial data in Python)
- Writing functions that return structured data
- How Income Statement → Cash Flow → Balance Sheet link together
- Financial ratio calculations
- The difference between cash and accrual concepts (depreciation, principal)

HOW THE 3 STATEMENTS LINK:
  Income Statement  →  Pre-Tax Income flows into Cash Flow Statement
  Cash Flow Statement →  Add back depreciation, subtract principal = ending cash
  Balance Sheet  →  Ending cash from CF, accumulated depreciation, loan paydown

WHY PYTHON INSTEAD OF EXCEL:
  1. No circular reference risk (Excel's #1 modeling headache)
  2. Assumptions change in ONE place (config.py), model recalculates everywhere
  3. You can run 1,000 scenarios in seconds (Module 3)
  4. Version control with git (Excel can't do this cleanly)
  5. Reproducible — anyone can run your model and get the same answer
"""

import pandas as pd
from config import ASSUMPTIONS, OPEX_BUDGET

# =============================================================================
# PYTHON CONCEPT: pandas
# =============================================================================
# pandas is THE library for working with tabular data in Python.
# A DataFrame is like an Excel spreadsheet: rows and columns.
# A Series is a single column.
#
# Key operations you'll learn here:
#   pd.DataFrame(data)      — create a table from a dictionary or list
#   df["column"]            — select a column
#   df.loc[row, col]        — select specific cells
#   df.sum(), df.cumsum()   — aggregate functions
#   df.to_dict()            — convert back to a Python dictionary


# =============================================================================
# INCOME STATEMENT
# =============================================================================

def build_income_statement(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = None,
) -> pd.DataFrame:
    """
    Build a multi-year income statement.

    Parameters:
        daily_device_hours: Override base case (default: 100)
        price_per_hour:     Override pricing (default: $9.00)
        forecast_years:     Override projection period (default: 3)

    Returns:
        pd.DataFrame with rows = line items, columns = Year 1, Year 2, ...

    PYTHON CONCEPT: Default arguments with None + fallback to config.
    This pattern lets callers override any assumption without touching config.py.
    The scenario module (Module 3) uses this heavily.
    """
    # --- Pull assumptions (use overrides if provided) ---
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]
    years = forecast_years or a["model"]["forecast_years"]
    rev_growth = a["growth"]["annual_revenue_growth"]
    exp_growth = a["growth"]["annual_expense_growth"]
    fnb_rev_y1 = a["fnb"]["year1_revenue"]
    cogs_pct = a["fnb"]["cogs_pct"]
    merchant_pct = a["fees"]["merchant_processing_pct"]
    depreciation = a["depreciation"]["annual_depreciation"]

    # --- Year 1 base calculations ---
    gaming_rev_y1 = hours * price * a["capacity"]["days_per_year"]

    # --- Build year-by-year columns ---
    # PYTHON CONCEPT: We build a dictionary where each key is a year label
    # and each value is a dictionary of line items. Then we convert to DataFrame.
    data = {}

    for yr in range(years):
        label = f"Year {yr + 1}"
        growth_factor = (1 + rev_growth) ** yr
        exp_factor = (1 + exp_growth) ** yr

        # Revenue
        gaming_rev = gaming_rev_y1 * growth_factor
        fnb_rev = fnb_rev_y1 * growth_factor
        total_revenue = gaming_rev + fnb_rev

        # COGS
        fnb_cogs = fnb_rev * cogs_pct
        gross_profit = total_revenue - fnb_cogs
        gross_margin = gross_profit / total_revenue if total_revenue else 0

        # Operating Expenses
        # Merchant fees scale with revenue (variable cost)
        merchant_fees = total_revenue * merchant_pct

        # All other OpEx grows at expense growth rate
        # EXCEPT merchant fees (already calculated from revenue)
        opex_lines = {}
        for name, category, base_amount in OPEX_BUDGET:
            if name == "Merchant & Card Processing Fees":
                opex_lines[name] = merchant_fees
            else:
                opex_lines[name] = base_amount * exp_factor

        total_opex_ex_dep = sum(opex_lines.values())
        total_opex_inc_dep = total_opex_ex_dep + depreciation

        # Profitability
        ebit = gross_profit - total_opex_inc_dep
        ebitda = ebit + depreciation

        # Interest expense (on beginning-of-year loan balance)
        beginning_loan = a["debt"]["loan_amount"] - (a["debt"]["annual_principal_payment"] * yr)
        interest_expense = beginning_loan * a["debt"]["interest_rate"]

        pretax_income = ebit - interest_expense

        # --- Store in the data dictionary ---
        data[label] = {
            "Gaming Revenue": gaming_rev,
            "F&B / Merchandise Revenue": fnb_rev,
            "Total Revenue": total_revenue,
            "": None,  # blank spacer row
            "F&B / Merchandise COGS": fnb_cogs,
            "Gross Profit": gross_profit,
            "Gross Margin %": gross_margin,
            " ": None,  # spacer
            **{f"  {k}": v for k, v in opex_lines.items()},
            "Depreciation Expense": depreciation,
            "Total Operating Expenses": total_opex_inc_dep,
            "  ": None,  # spacer
            "EBIT (Operating Income)": ebit,
            "EBITDA": ebitda,
            "EBITDA Margin %": ebitda / total_revenue if total_revenue else 0,
            "   ": None,  # spacer
            "Interest Expense": interest_expense,
            "Pre-Tax Income": pretax_income,
            "Pre-Tax Margin %": pretax_income / total_revenue if total_revenue else 0,
        }

    # PYTHON CONCEPT: pd.DataFrame.from_dict with orient="index" creates
    # a DataFrame where dict keys become column headers.
    df = pd.DataFrame(data)
    return df


# =============================================================================
# CASH FLOW STATEMENT
# =============================================================================

def build_cash_flow_statement(
    income_statement: pd.DataFrame = None,
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = None,
) -> pd.DataFrame:
    """
    Build a simplified cash flow statement from the income statement.

    KEY CONCEPT: Why cash flow ≠ net income
    - Depreciation is a non-cash expense. It reduces income but doesn't
      leave the bank account. So we ADD IT BACK to get cash from operations.
    - Principal repayment is NOT an expense (it's a balance sheet event),
      but it DOES use cash. So it appears in cash from financing.
    """
    a = ASSUMPTIONS
    years = forecast_years or a["model"]["forecast_years"]

    # Build income statement if not provided
    if income_statement is None:
        income_statement = build_income_statement(
            daily_device_hours=daily_device_hours,
            price_per_hour=price_per_hour,
            forecast_years=years,
        )

    data = {}
    beginning_cash = a["debt"]["owner_equity"]  # Start with $20,000 equity

    for yr in range(years):
        label = f"Year {yr + 1}"

        pretax_income = income_statement.loc["Pre-Tax Income", label]
        depreciation = a["depreciation"]["annual_depreciation"]
        principal = a["debt"]["annual_principal_payment"]

        cash_from_ops = pretax_income + depreciation
        cash_from_financing = -principal
        net_change = cash_from_ops + cash_from_financing
        ending_cash = beginning_cash + net_change

        data[label] = {
            "Cash Flow from Operations": None,
            "  Pre-Tax Income": pretax_income,
            "  Add: Depreciation": depreciation,
            "Net Cash from Operations": cash_from_ops,
            "": None,
            "Cash Flow from Financing": None,
            "  Principal Repayment": -principal,
            "Net Cash from Financing": cash_from_financing,
            " ": None,
            "Net Change in Cash": net_change,
            "  ": None,
            "Beginning Cash Balance": beginning_cash,
            "Ending Cash Balance": ending_cash,
        }

        # Next year's beginning cash = this year's ending cash
        # PYTHON CONCEPT: State carries forward. This is how linked models work.
        beginning_cash = ending_cash

    return pd.DataFrame(data)


# =============================================================================
# BALANCE SHEET
# =============================================================================

def build_balance_sheet(
    cash_flow: pd.DataFrame = None,
    income_statement: pd.DataFrame = None,
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = None,
) -> pd.DataFrame:
    """
    Build end-of-year balance sheets.

    KEY CONCEPT: The accounting equation
      Assets = Liabilities + Owner's Equity
      This MUST balance. If it doesn't, the model has an error.
    """
    a = ASSUMPTIONS
    years = forecast_years or a["model"]["forecast_years"]

    if income_statement is None:
        income_statement = build_income_statement(
            daily_device_hours=daily_device_hours,
            price_per_hour=price_per_hour,
            forecast_years=years,
        )
    if cash_flow is None:
        cash_flow = build_cash_flow_statement(
            income_statement=income_statement,
            forecast_years=years,
        )

    data = {}
    cumulative_earnings = 0.0

    for yr in range(years):
        label = f"Year {yr + 1}"

        # Assets
        cash = cash_flow.loc["Ending Cash Balance", label]
        gross_ppe = a["depreciation"]["depreciable_assets"]
        accum_dep = a["depreciation"]["annual_depreciation"] * (yr + 1)
        net_ppe = gross_ppe - accum_dep
        total_assets = cash + net_ppe

        # Liabilities
        loan_balance = a["debt"]["loan_amount"] - (a["debt"]["annual_principal_payment"] * (yr + 1))

        # Equity
        initial_capital = a["debt"]["owner_equity"]
        pretax_income = income_statement.loc["Pre-Tax Income", label]
        cumulative_earnings += pretax_income
        total_equity = initial_capital + cumulative_earnings

        # Balance check
        total_liab_equity = loan_balance + total_equity
        balance_check = abs(total_assets - total_liab_equity) < 0.01

        data[label] = {
            "ASSETS": None,
            "Current Assets": None,
            "  Cash": cash,
            "Total Current Assets": cash,
            "": None,
            "Fixed Assets": None,
            "  Property & Equipment at Cost": gross_ppe,
            "  Less: Accumulated Depreciation": -accum_dep,
            "Net Property & Equipment": net_ppe,
            " ": None,
            "TOTAL ASSETS": total_assets,
            "  ": None,
            "LIABILITIES AND EQUITY": None,
            "  SBA Term Loan Balance": loan_balance,
            "Total Liabilities": loan_balance,
            "   ": None,
            "Owner Equity": None,
            "  Initial Capital": initial_capital,
            "  Retained Earnings": cumulative_earnings,
            "Total Owner Equity": total_equity,
            "    ": None,
            "TOTAL LIABILITIES & EQUITY": total_liab_equity,
            "     ": None,
            "Balance Check Passes": balance_check,
        }

    return pd.DataFrame(data)


# =============================================================================
# KEY FINANCIAL RATIOS
# =============================================================================

def calculate_ratios(
    income_statement: pd.DataFrame,
    cash_flow: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate key financial ratios for each year.

    WHAT THESE RATIOS MEAN:
    - Gross Margin: How much you keep after direct costs. >95% is very high (service biz).
    - EBITDA Margin: Operating profitability before non-cash and financing. Key for lenders.
    - DSCR: Can you pay your debt? EBITDA ÷ (Interest + Principal). SBA wants >1.25x.
    - Debt-to-Equity: How leveraged are you? Higher = more risk.
    - Utilization: Are you filling seats? The #1 operational KPI for this business.
    - Cash Runway: Months of OpEx you could cover with cash on hand.

    PYTHON CONCEPT: Building a summary DataFrame by extracting values from
    other DataFrames. This is a common pattern in financial analysis.
    """
    a = ASSUMPTIONS
    data = {}

    for label in income_statement.columns:
        total_rev = income_statement.loc["Total Revenue", label]
        gross_profit = income_statement.loc["Gross Profit", label]
        ebitda = income_statement.loc["EBITDA", label]
        ebit = income_statement.loc["EBIT (Operating Income)", label]
        pretax = income_statement.loc["Pre-Tax Income", label]
        interest = income_statement.loc["Interest Expense", label]
        cash = cash_flow.loc["Ending Cash Balance", label]
        total_assets = balance_sheet.loc["TOTAL ASSETS", label]
        total_debt = balance_sheet.loc["Total Liabilities", label]
        total_equity = balance_sheet.loc["Total Owner Equity", label]

        principal = a["debt"]["annual_principal_payment"]
        total_debt_service = interest + principal

        # Monthly OpEx approximation
        monthly_opex = (total_rev - gross_profit + sum(
            amount for _, _, amount in OPEX_BUDGET
        )) / 12

        data[label] = {
            "Gross Margin": gross_profit / total_rev if total_rev else 0,
            "EBITDA Margin": ebitda / total_rev if total_rev else 0,
            "Pre-Tax Margin": pretax / total_rev if total_rev else 0,
            "DSCR": ebitda / total_debt_service if total_debt_service else 0,
            "Debt-to-Equity": total_debt / total_equity if total_equity else 0,
            "Return on Assets": pretax / total_assets if total_assets else 0,
            "Return on Equity": pretax / total_equity if total_equity else 0,
            "Cash Balance": cash,
            "Cash Runway (months)": cash / monthly_opex if monthly_opex else 0,
        }

    return pd.DataFrame(data)


# =============================================================================
# CONVENIENCE: BUILD EVERYTHING AT ONCE
# =============================================================================

def build_full_model(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = None,
) -> dict:
    """
    Build all 3 statements + ratios in one call.

    Returns a dictionary with keys:
      "income_statement", "cash_flow", "balance_sheet", "ratios"

    PYTHON CONCEPT: Returning a dict of DataFrames. This is a clean way to
    bundle related outputs. The caller can access any piece:
      model = build_full_model()
      model["income_statement"]  →  the IS DataFrame
      model["ratios"]            →  the ratios DataFrame

    This is the function that Module 3 (scenarios) and Module 4 (Excel)
    will call repeatedly with different inputs.
    """
    inc = build_income_statement(daily_device_hours, price_per_hour, forecast_years)
    cf = build_cash_flow_statement(income_statement=inc, forecast_years=forecast_years)
    bs = build_balance_sheet(income_statement=inc, cash_flow=cf, forecast_years=forecast_years)
    ratios = calculate_ratios(inc, cf, bs)

    return {
        "income_statement": inc,
        "cash_flow": cf,
        "balance_sheet": bs,
        "ratios": ratios,
    }


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GAMING ARENA — 3-STATEMENT MODEL (BASE CASE)")
    print("=" * 70)

    model = build_full_model()

    # --- Income Statement ---
    print("\nINCOME STATEMENT")
    print("-" * 70)
    is_df = model["income_statement"]
    for idx, row in is_df.iterrows():
        label = idx.strip() if isinstance(idx, str) else str(idx)
        if row.isna().all():
            print()
            continue
        vals = "  ".join(
            f"${v:>12,.0f}" if isinstance(v, (int, float)) and abs(v) > 1
            else f"  {v:>11.1%} " if isinstance(v, float) and abs(v) <= 1
            else f"  {str(v):>12s} "
            for v in row
        )
        print(f"  {label:<42s} {vals}")

    # --- Key Ratios ---
    print("\n\nKEY RATIOS")
    print("-" * 70)
    ratios = model["ratios"]
    for idx, row in ratios.iterrows():
        vals = "  ".join(
            f"  {v:>11.1%} " if "Margin" in idx or "Return" in idx
            else f"  {v:>10.2f}x " if "DSCR" in idx or "Debt" in idx
            else f"  {v:>10.1f}  " if "months" in idx.lower()
            else f"${v:>12,.0f}"
            for v in row
        )
        print(f"  {idx:<30s} {vals}")

    # --- Balance Check ---
    bs = model["balance_sheet"]
    print("\n\nBALANCE SHEET VERIFICATION")
    print("-" * 70)
    for label in bs.columns:
        assets = bs.loc["TOTAL ASSETS", label]
        liab_eq = bs.loc["TOTAL LIABILITIES & EQUITY", label]
        check = bs.loc["Balance Check Passes", label]
        status = "PASSES" if check else "FAILS"
        print(f"  {label}: Assets=${assets:,.0f}  L+E=${liab_eq:,.0f}  → {status}")
