"""
MODULE 7: BUDGET VS ACTUAL VARIANCE ANALYSIS
===============================================
Gaming Arena, LLC -- Variance Analysis Engine

WHAT THIS FILE TEACHES YOU:
- Budget vs Actual comparison (THE most common FP&A skill)
- Variance calculations ($ difference and % difference)
- Materiality thresholds (flagging what matters)
- Favorable vs Unfavorable classification
- Waterfall decomposition (breaking total variance into drivers)
- Period-over-period trend analysis
- Automated variance commentary generation

WHY THIS MATTERS FOR FP&A ROLES:
  Every single FP&A job description asks for variance analysis.
  "Analyze budget vs actual" / "explain performance discrepancies" /
  "monthly financial reviews" -- this module shows you can build
  the engine behind those deliverables, not just fill in a template.

PYTHON CONCEPTS:
- Dictionary comprehension for building budget/actual datasets
- Conditional logic for favorable/unfavorable classification
- String formatting for professional variance commentary
- Sorting and filtering DataFrames by materiality
"""

import pandas as pd
import numpy as np
from config import ASSUMPTIONS, OPEX_BUDGET, calc_gaming_revenue
from model_engine import build_income_statement


# =============================================================================
# BUDGET DATA
# =============================================================================
# CONCEPT: In real FP&A, the budget is set at the beginning of the year
# and doesn't change. Actuals come in monthly. Here we simulate both.
#
# The BUDGET is your base case model output (what you projected).
# The ACTUALS introduce realistic variance -- some lines come in
# over budget, some under.

def build_budget(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> dict:
    """
    Build the annual budget from model assumptions.
    This represents what was PLANNED at the start of the year.

    Returns a dictionary of {line_item: budgeted_amount}.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]
    days = a["capacity"]["days_per_year"]

    gaming_rev = hours * price * days
    fnb_rev = a["fnb"]["year1_revenue"]
    total_rev = gaming_rev + fnb_rev

    fnb_cogs = fnb_rev * a["fnb"]["cogs_pct"]
    gross_profit = total_rev - fnb_cogs

    # Operating expenses from budget
    opex = {}
    merchant_fees = total_rev * a["fees"]["merchant_processing_pct"]
    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            opex[name] = merchant_fees
        else:
            opex[name] = base_amount

    total_opex = sum(opex.values()) + a["depreciation"]["annual_depreciation"]
    ebitda = gross_profit - sum(opex.values())
    ebit = gross_profit - total_opex

    beginning_loan = a["debt"]["loan_amount"]
    interest = beginning_loan * a["debt"]["interest_rate"]
    pretax = ebit - interest

    budget = {
        "Gaming Revenue": gaming_rev,
        "F&B / Merchandise Revenue": fnb_rev,
        "Total Revenue": total_rev,
        "F&B / Merchandise COGS": fnb_cogs,
        "Gross Profit": gross_profit,
        **opex,
        "Depreciation Expense": a["depreciation"]["annual_depreciation"],
        "Total Operating Expenses": total_opex,
        "EBITDA": ebitda,
        "EBIT (Operating Income)": ebit,
        "Interest Expense": interest,
        "Pre-Tax Income": pretax,
    }

    return budget


def build_actuals(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    seed: int = 42,
) -> dict:
    """
    Simulate actual results with realistic variance from budget.

    CONCEPT: In real life, actuals come from your ERP/accounting system.
    Here we simulate them by applying random but realistic adjustments
    to the budget. This lets you practice the analysis workflow.

    Each line item gets a variance driver:
    - Revenue: driven by actual utilization (hours) and pricing
    - Variable costs: scale with revenue
    - Fixed costs: random walk around budget (+/- 5-15%)
    """
    a = ASSUMPTIONS
    rng = np.random.RandomState(seed)

    budget_hours = daily_device_hours or a["utilization"]["base_case_hours"]
    budget_price = price_per_hour or a["pricing"]["price_per_hour"]
    days = a["capacity"]["days_per_year"]

    # Simulate actual utilization and pricing
    # Hours came in slightly below budget, price held steady
    actual_hours = budget_hours + rng.randint(-12, 6)
    actual_price = budget_price + rng.uniform(-0.25, 0.50)

    gaming_rev = actual_hours * actual_price * days
    fnb_rev = a["fnb"]["year1_revenue"] * (1 + rng.uniform(-0.05, 0.08))
    total_rev = gaming_rev + fnb_rev

    fnb_cogs = fnb_rev * (a["fnb"]["cogs_pct"] + rng.uniform(-0.02, 0.03))
    gross_profit = total_rev - fnb_cogs

    # Operating expenses -- each gets independent variance
    opex = {}
    merchant_fees = total_rev * a["fees"]["merchant_processing_pct"]
    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            opex[name] = merchant_fees
        elif name in ["Rent and CAM", "Insurance"]:
            # Contractual -- very little variance
            opex[name] = base_amount * (1 + rng.uniform(-0.01, 0.02))
        elif name in ["Part-Time Wages", "Payroll Taxes and Benefits"]:
            # Labor -- moderate variance (overtime, scheduling)
            opex[name] = base_amount * (1 + rng.uniform(-0.03, 0.08))
        elif name in ["Marketing and Advertising", "Tournament Prizes"]:
            # Discretionary -- can swing more
            opex[name] = base_amount * (1 + rng.uniform(-0.10, 0.15))
        else:
            # Everything else -- small variance
            opex[name] = base_amount * (1 + rng.uniform(-0.05, 0.07))

    depreciation = a["depreciation"]["annual_depreciation"]
    total_opex = sum(opex.values()) + depreciation
    ebitda = gross_profit - sum(opex.values())
    ebit = gross_profit - total_opex

    beginning_loan = a["debt"]["loan_amount"]
    interest = beginning_loan * a["debt"]["interest_rate"]
    pretax = ebit - interest

    actuals = {
        "Gaming Revenue": gaming_rev,
        "F&B / Merchandise Revenue": fnb_rev,
        "Total Revenue": total_rev,
        "F&B / Merchandise COGS": fnb_cogs,
        "Gross Profit": gross_profit,
        **opex,
        "Depreciation Expense": depreciation,
        "Total Operating Expenses": total_opex,
        "EBITDA": ebitda,
        "EBIT (Operating Income)": ebit,
        "Interest Expense": interest,
        "Pre-Tax Income": pretax,
    }

    return actuals


# =============================================================================
# VARIANCE CALCULATION ENGINE
# =============================================================================

# Line items where HIGHER actual = FAVORABLE (revenue, profit lines)
REVENUE_AND_PROFIT_LINES = {
    "Gaming Revenue", "F&B / Merchandise Revenue", "Total Revenue",
    "Gross Profit", "EBITDA", "EBIT (Operating Income)", "Pre-Tax Income",
}

# Line items where LOWER actual = FAVORABLE (cost/expense lines)
COST_LINES = {
    "F&B / Merchandise COGS", "Merchant & Card Processing Fees",
    "Rent and CAM", "Utilities and Internet", "Insurance",
    "Owner Salary", "Part-Time Wages", "Payroll Taxes and Benefits",
    "Tournament Prizes", "Software and IT Subscriptions",
    "Marketing and Advertising", "Repairs and Maintenance",
    "Miscellaneous / Contingency", "Depreciation Expense",
    "Total Operating Expenses", "Interest Expense",
}


def compute_variance(
    budget: dict,
    actuals: dict,
    materiality_threshold_pct: float = 0.05,
    materiality_threshold_dollar: float = 1000,
) -> pd.DataFrame:
    """
    Compute line-by-line variance between budget and actuals.

    CONCEPT: Variance = Actual - Budget
    For REVENUE lines: positive variance = favorable (beat budget)
    For EXPENSE lines: negative variance = favorable (spent less)

    Materiality: Not every variance matters. A $50 variance on a $78,000
    rent line is noise. Materiality thresholds filter out the noise
    so management focuses on what actually moved the needle.

    Returns DataFrame with columns:
    - Budget, Actual, Variance ($), Variance (%), Direction, Material
    """
    rows = []

    for line_item in budget:
        if line_item not in actuals:
            continue

        b = budget[line_item]
        a = actuals[line_item]
        var_dollar = a - b
        var_pct = var_dollar / abs(b) if b != 0 else 0

        # Determine if favorable or unfavorable
        if line_item in REVENUE_AND_PROFIT_LINES:
            direction = "Favorable" if var_dollar >= 0 else "Unfavorable"
        elif line_item in COST_LINES:
            direction = "Favorable" if var_dollar <= 0 else "Unfavorable"
        else:
            direction = "Neutral"

        # Materiality check
        is_material = (
            abs(var_pct) >= materiality_threshold_pct
            or abs(var_dollar) >= materiality_threshold_dollar
        )

        rows.append({
            "Line Item": line_item,
            "Budget": b,
            "Actual": a,
            "Variance ($)": var_dollar,
            "Variance (%)": var_pct,
            "Direction": direction,
            "Material": is_material,
        })

    df = pd.DataFrame(rows).set_index("Line Item")
    return df


# =============================================================================
# WATERFALL DECOMPOSITION
# =============================================================================

def build_variance_waterfall(variance_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a waterfall showing how individual line variances
    bridge from budgeted Pre-Tax Income to actual Pre-Tax Income.

    CONCEPT: A variance waterfall answers the question:
    "We budgeted $X pre-tax income but got $Y. What drove the difference?"

    It decomposes the total variance into revenue drivers,
    COGS impact, and individual OpEx line movements.

    This is the core deliverable in monthly financial reviews.
    """
    # Start with budgeted pre-tax income
    budget_pretax = variance_df.loc["Pre-Tax Income", "Budget"]

    # Build waterfall items
    waterfall = []

    # Revenue variance
    if "Total Revenue" in variance_df.index:
        rev_var = variance_df.loc["Total Revenue", "Variance ($)"]
        waterfall.append({
            "Driver": "Revenue variance",
            "Impact ($)": rev_var,
            "Direction": "Favorable" if rev_var >= 0 else "Unfavorable",
        })

    # COGS variance (sign flipped -- higher COGS is unfavorable)
    if "F&B / Merchandise COGS" in variance_df.index:
        cogs_var = variance_df.loc["F&B / Merchandise COGS", "Variance ($)"]
        waterfall.append({
            "Driver": "COGS variance",
            "Impact ($)": -cogs_var,  # flip sign: higher cost = negative impact
            "Direction": "Favorable" if cogs_var <= 0 else "Unfavorable",
        })

    # Individual OpEx variances (only material ones)
    opex_lines = [
        item for item in variance_df.index
        if item in COST_LINES
        and item not in {
            "F&B / Merchandise COGS", "Total Operating Expenses",
            "Depreciation Expense", "Interest Expense",
        }
        and variance_df.loc[item, "Material"]
    ]

    for line in opex_lines:
        var = variance_df.loc[line, "Variance ($)"]
        waterfall.append({
            "Driver": line,
            "Impact ($)": -var,  # flip: higher expense = negative impact on income
            "Direction": "Favorable" if var <= 0 else "Unfavorable",
        })

    # Non-material OpEx lumped together
    non_material_opex = [
        item for item in variance_df.index
        if item in COST_LINES
        and item not in {
            "F&B / Merchandise COGS", "Total Operating Expenses",
            "Depreciation Expense", "Interest Expense",
        }
        and not variance_df.loc[item, "Material"]
    ]
    if non_material_opex:
        other_var = sum(variance_df.loc[line, "Variance ($)"] for line in non_material_opex)
        waterfall.append({
            "Driver": "Other OpEx (non-material)",
            "Impact ($)": -other_var,
            "Direction": "Favorable" if other_var <= 0 else "Unfavorable",
        })

    # Depreciation variance
    if "Depreciation Expense" in variance_df.index:
        dep_var = variance_df.loc["Depreciation Expense", "Variance ($)"]
        if abs(dep_var) > 0:
            waterfall.append({
                "Driver": "Depreciation variance",
                "Impact ($)": -dep_var,
                "Direction": "Favorable" if dep_var <= 0 else "Unfavorable",
            })

    # Interest variance
    if "Interest Expense" in variance_df.index:
        int_var = variance_df.loc["Interest Expense", "Variance ($)"]
        if abs(int_var) > 0:
            waterfall.append({
                "Driver": "Interest expense variance",
                "Impact ($)": -int_var,
                "Direction": "Favorable" if int_var <= 0 else "Unfavorable",
            })

    df = pd.DataFrame(waterfall)

    # Add running total for waterfall chart
    if not df.empty:
        df["Running Total"] = budget_pretax + df["Impact ($)"].cumsum()

    return df


# =============================================================================
# MONTHLY TREND ANALYSIS
# =============================================================================

def build_monthly_actuals(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate simulated monthly actuals for trend analysis.

    CONCEPT: Period-over-period trend analysis shows whether
    performance is improving, declining, or seasonal. Every FP&A
    role requires this for monthly reporting packages.

    Returns a DataFrame with monthly P&L data including
    month-over-month and cumulative YTD columns.
    """
    a = ASSUMPTIONS
    rng = np.random.RandomState(seed)

    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]
    days_per_month = a["capacity"]["days_per_year"] / 12

    # Seasonality factors (gaming arenas are busier in summer and holidays)
    seasonality = {
        "Jan": 0.85, "Feb": 0.80, "Mar": 0.90,
        "Apr": 0.95, "May": 1.00, "Jun": 1.15,
        "Jul": 1.20, "Aug": 1.15, "Sep": 0.95,
        "Oct": 1.00, "Nov": 1.05, "Dec": 1.10,
    }

    months = list(seasonality.keys())
    monthly_data = []

    for i, month in enumerate(months):
        factor = seasonality[month]

        # Hours vary by season + random noise
        m_hours = hours * factor + rng.randint(-8, 8)
        m_price = price + rng.uniform(-0.15, 0.15)
        m_days = days_per_month + rng.randint(-1, 2)

        gaming_rev = m_hours * m_price * m_days
        fnb_rev = (a["fnb"]["year1_revenue"] / 12) * factor
        total_rev = gaming_rev + fnb_rev

        fnb_cogs = fnb_rev * a["fnb"]["cogs_pct"]
        gross_profit = total_rev - fnb_cogs

        # Monthly OpEx (annual / 12 with variance)
        monthly_opex = 0
        for name, category, base_amount in OPEX_BUDGET:
            if name == "Merchant & Card Processing Fees":
                monthly_opex += total_rev * a["fees"]["merchant_processing_pct"]
            else:
                monthly_opex += (base_amount / 12) * (1 + rng.uniform(-0.05, 0.05))

        depreciation = a["depreciation"]["annual_depreciation"] / 12
        ebitda = gross_profit - monthly_opex
        ebit = ebitda - depreciation
        interest = (a["debt"]["loan_amount"] * a["debt"]["interest_rate"]) / 12
        pretax = ebit - interest

        # Monthly budget (straight-line, no seasonality)
        budget_gaming = hours * price * days_per_month
        budget_fnb = a["fnb"]["year1_revenue"] / 12
        budget_total_rev = budget_gaming + budget_fnb
        budget_cogs = budget_fnb * a["fnb"]["cogs_pct"]
        budget_gross = budget_total_rev - budget_cogs

        budget_opex = 0
        for name, category, base_amount in OPEX_BUDGET:
            if name == "Merchant & Card Processing Fees":
                budget_opex += budget_total_rev * a["fees"]["merchant_processing_pct"]
            else:
                budget_opex += base_amount / 12

        budget_ebitda = budget_gross - budget_opex
        budget_ebit = budget_ebitda - depreciation
        budget_pretax = budget_ebit - interest

        monthly_data.append({
            "Month": month,
            "Actual Revenue": total_rev,
            "Budget Revenue": budget_total_rev,
            "Revenue Variance ($)": total_rev - budget_total_rev,
            "Revenue Variance (%)": (total_rev - budget_total_rev) / budget_total_rev,
            "Actual Gross Profit": gross_profit,
            "Budget Gross Profit": budget_gross,
            "Actual EBITDA": ebitda,
            "Budget EBITDA": budget_ebitda,
            "EBITDA Variance ($)": ebitda - budget_ebitda,
            "EBITDA Variance (%)": (ebitda - budget_ebitda) / budget_ebitda if budget_ebitda else 0,
            "Actual Pre-Tax": pretax,
            "Budget Pre-Tax": budget_pretax,
            "Actual Hours": m_hours,
            "Budget Hours": hours,
            "Actual Price": m_price,
        })

    df = pd.DataFrame(monthly_data).set_index("Month")

    # Add YTD cumulative columns
    df["YTD Actual Revenue"] = df["Actual Revenue"].cumsum()
    df["YTD Budget Revenue"] = df["Budget Revenue"].cumsum()
    df["YTD Revenue Variance ($)"] = df["YTD Actual Revenue"] - df["YTD Budget Revenue"]
    df["YTD Actual EBITDA"] = df["Actual EBITDA"].cumsum()
    df["YTD Budget EBITDA"] = df["Budget EBITDA"].cumsum()

    return df


# =============================================================================
# VARIANCE COMMENTARY GENERATOR
# =============================================================================

def generate_variance_commentary(
    variance_df: pd.DataFrame,
    top_n: int = 5,
) -> list:
    """
    Auto-generate plain-English variance commentary for material items.

    CONCEPT: Variance commentary is what you write in the monthly
    reporting package to explain WHY numbers moved. Automating this
    saves hours of manual work and ensures consistency.

    Every FP&A analyst writes these. Showing you can BUILD the
    automation is what separates you from candidates who just
    fill in templates.
    """
    # Filter to material variances only, sort by absolute dollar impact
    material = variance_df[variance_df["Material"]].copy()
    material["Abs Variance"] = material["Variance ($)"].abs()
    material = material.sort_values("Abs Variance", ascending=False).head(top_n)

    commentary = []

    for line_item, row in material.iterrows():
        var_dollar = row["Variance ($)"]
        var_pct = row["Variance (%)"]
        direction = row["Direction"]
        budget = row["Budget"]
        actual = row["Actual"]

        # Build the commentary sentence
        if line_item in REVENUE_AND_PROFIT_LINES:
            if var_dollar >= 0:
                action = "exceeded budget"
            else:
                action = "fell short of budget"
        else:
            if var_dollar > 0:
                action = "came in over budget"
            else:
                action = "came in under budget"

        comment = (
            f"{line_item}: {action} by ${abs(var_dollar):,.0f} ({abs(var_pct):.1%}). "
            f"Budget: ${budget:,.0f} | Actual: ${actual:,.0f}. "
            f"[{direction.upper()}]"
        )
        commentary.append(comment)

    return commentary


# =============================================================================
# KPI SCORECARD
# =============================================================================

def build_kpi_scorecard(
    budget: dict,
    actuals: dict,
) -> pd.DataFrame:
    """
    Build a KPI scorecard with targets, actuals, and RAG status.

    CONCEPT: A KPI scorecard is a one-page summary that tells
    management "are we on track?" Red/Amber/Green (RAG) status
    makes it instantly scannable.

    RAG logic:
    - GREEN: within 5% of target (or better)
    - AMBER: 5-15% off target
    - RED: more than 15% off target
    """
    b_rev = budget["Total Revenue"]
    a_rev = actuals["Total Revenue"]
    b_gp = budget["Gross Profit"]
    a_gp = actuals["Gross Profit"]
    b_ebitda = budget["EBITDA"]
    a_ebitda = actuals["EBITDA"]
    b_pretax = budget["Pre-Tax Income"]
    a_pretax = actuals["Pre-Tax Income"]
    b_opex = budget["Total Operating Expenses"]
    a_opex = actuals["Total Operating Expenses"]

    a_assumptions = ASSUMPTIONS
    loan = a_assumptions["debt"]["loan_amount"]
    annual_debt_service = (
        a_assumptions["debt"]["annual_principal_payment"]
        + loan * a_assumptions["debt"]["interest_rate"]
    )

    kpis = [
        {
            "KPI": "Total Revenue",
            "Target": b_rev,
            "Actual": a_rev,
            "Unit": "$",
            "Higher Is Better": True,
        },
        {
            "KPI": "Gross Margin",
            "Target": b_gp / b_rev if b_rev else 0,
            "Actual": a_gp / a_rev if a_rev else 0,
            "Unit": "%",
            "Higher Is Better": True,
        },
        {
            "KPI": "EBITDA",
            "Target": b_ebitda,
            "Actual": a_ebitda,
            "Unit": "$",
            "Higher Is Better": True,
        },
        {
            "KPI": "EBITDA Margin",
            "Target": b_ebitda / b_rev if b_rev else 0,
            "Actual": a_ebitda / a_rev if a_rev else 0,
            "Unit": "%",
            "Higher Is Better": True,
        },
        {
            "KPI": "Total OpEx",
            "Target": b_opex,
            "Actual": a_opex,
            "Unit": "$",
            "Higher Is Better": False,
        },
        {
            "KPI": "Pre-Tax Income",
            "Target": b_pretax,
            "Actual": a_pretax,
            "Unit": "$",
            "Higher Is Better": True,
        },
        {
            "KPI": "DSCR",
            "Target": 1.25,
            "Actual": (a_pretax + a_assumptions["depreciation"]["annual_depreciation"]) / annual_debt_service,
            "Unit": "x",
            "Higher Is Better": True,
        },
        {
            "KPI": "OpEx as % of Revenue",
            "Target": b_opex / b_rev if b_rev else 0,
            "Actual": a_opex / a_rev if a_rev else 0,
            "Unit": "%",
            "Higher Is Better": False,
        },
    ]

    # Calculate variance and RAG status
    for kpi in kpis:
        target = kpi["Target"]
        actual = kpi["Actual"]
        higher_better = kpi["Higher Is Better"]

        if target != 0:
            var_pct = (actual - target) / abs(target)
        else:
            var_pct = 0

        # Performance score: positive = good, negative = bad
        perf = var_pct if higher_better else -var_pct

        if perf >= -0.05:
            rag = "GREEN"
        elif perf >= -0.15:
            rag = "AMBER"
        else:
            rag = "RED"

        kpi["Variance (%)"] = var_pct
        kpi["RAG"] = rag

    df = pd.DataFrame(kpis)
    df = df[["KPI", "Target", "Actual", "Variance (%)", "RAG", "Unit"]]
    return df


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 7: BUDGET VS ACTUAL VARIANCE ANALYSIS")
    print("=" * 70)

    # Build budget and actuals
    budget = build_budget()
    actuals = build_actuals()

    print("\n--- Annual Variance Report ---")
    variance = compute_variance(budget, actuals)

    # Display formatted
    for line_item, row in variance.iterrows():
        flag = " *** " if row["Material"] else "     "
        print(
            f"{flag}{line_item:40s}  "
            f"Budget: ${row['Budget']:>10,.0f}  "
            f"Actual: ${row['Actual']:>10,.0f}  "
            f"Var: ${row['Variance ($)']:>+10,.0f}  "
            f"({row['Variance (%)']:>+6.1%})  "
            f"{row['Direction']}"
        )

    print("\n--- Variance Waterfall ---")
    waterfall = build_variance_waterfall(variance)
    for _, row in waterfall.iterrows():
        print(f"  {row['Driver']:40s}  ${row['Impact ($)']:>+10,.0f}  {row['Direction']}")

    print(f"\n  Budget Pre-Tax: ${variance.loc['Pre-Tax Income', 'Budget']:>10,.0f}")
    print(f"  Actual Pre-Tax: ${variance.loc['Pre-Tax Income', 'Actual']:>10,.0f}")

    print("\n--- Variance Commentary ---")
    commentary = generate_variance_commentary(variance)
    for i, comment in enumerate(commentary, 1):
        print(f"  {i}. {comment}")

    print("\n--- KPI Scorecard ---")
    scorecard = build_kpi_scorecard(budget, actuals)
    for _, row in scorecard.iterrows():
        if row["Unit"] == "$":
            t_fmt = f"${row['Target']:>10,.0f}"
            a_fmt = f"${row['Actual']:>10,.0f}"
        elif row["Unit"] == "%":
            t_fmt = f"{row['Target']:>10.1%}"
            a_fmt = f"{row['Actual']:>10.1%}"
        else:
            t_fmt = f"{row['Target']:>10.2f}x"
            a_fmt = f"{row['Actual']:>10.2f}x"

        print(
            f"  [{row['RAG']:>5s}]  {row['KPI']:25s}  "
            f"Target: {t_fmt}  Actual: {a_fmt}  "
            f"Var: {row['Variance (%)']:>+6.1%}"
        )

    print("\n--- Monthly Trend (first 6 months) ---")
    monthly = build_monthly_actuals()
    for month in list(monthly.index)[:6]:
        row = monthly.loc[month]
        print(
            f"  {month}  "
            f"Rev: ${row['Actual Revenue']:>8,.0f} vs ${row['Budget Revenue']:>8,.0f}  "
            f"Var: {row['Revenue Variance (%)']:>+6.1%}  "
            f"EBITDA: ${row['Actual EBITDA']:>8,.0f}"
        )

    print("\n--- YTD Summary (through December) ---")
    last = monthly.iloc[-1]
    print(f"  YTD Revenue:  Actual ${last['YTD Actual Revenue']:>10,.0f}  "
          f"Budget ${last['YTD Budget Revenue']:>10,.0f}  "
          f"Var ${last['YTD Revenue Variance ($)']:>+10,.0f}")
    print(f"  YTD EBITDA:   Actual ${last['YTD Actual EBITDA']:>10,.0f}  "
          f"Budget ${last['YTD Budget EBITDA']:>10,.0f}")
