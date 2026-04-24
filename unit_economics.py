"""
MODULE 9: UNIT ECONOMICS & DRIVER-BASED METRICS
==================================================
Gaming Arena, LLC — Operational Unit Economics Engine

WHAT THIS FILE TEACHES YOU:
- Driver-based modeling (THE top-tier FP&A skill)
- Unit economics (revenue and cost per unit of activity)
- Contribution margin analysis
- Equipment payback period
- Operational KPIs that tie financial results to business actions

WHY THIS MATTERS:
  Senior FP&A roles and CFO positions emphasize "driver-based
  forecasting" — understanding WHAT drives each line item, not
  just projecting trends. This module decomposes the P&L into
  per-unit metrics that operators can actually manage.

  When an interviewer asks "how would you forecast revenue?"
  the answer isn't "grow it 5%." It's "we have 40 stations,
  open 12 hours, at X% utilization and $Y/hour — here's
  what moves each variable and by how much."
"""

import pandas as pd
import numpy as np
from config import ASSUMPTIONS, OPEX_BUDGET, calc_startup_category_total, calc_total_startup_costs


def compute_unit_economics(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> dict:
    """
    Compute comprehensive unit-level economics.

    Returns a dictionary of metric groups, each containing
    individual metrics with value, unit, and explanation.

    CONCEPT: Unit economics answer "how much do we make/spend
    per unit of activity?" This is how you bridge from financial
    statements to operational decisions.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]

    stations = a["capacity"]["total_devices"]
    op_hours = a["capacity"]["operating_hours_per_day"]
    days = a["capacity"]["days_per_year"]
    max_daily_hours = stations * op_hours
    utilization = hours / max_daily_hours

    # Annual financials
    gaming_rev = hours * price * days
    fnb_rev = a["fnb"]["year1_revenue"]
    total_rev = gaming_rev + fnb_rev
    fnb_cogs = fnb_rev * a["fnb"]["cogs_pct"]
    gross_profit = total_rev - fnb_cogs

    # Total annual operating expenses
    total_opex = 0
    fixed_opex = 0
    variable_opex = 0
    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            amt = total_rev * a["fees"]["merchant_processing_pct"]
            variable_opex += amt
        else:
            amt = base_amount
            if category == "fixed":
                fixed_opex += amt
            elif category == "semi_variable":
                fixed_opex += amt * 0.6   # estimate 60% fixed
                variable_opex += amt * 0.4
            else:
                variable_opex += amt
        total_opex += amt

    depreciation = a["depreciation"]["annual_depreciation"]
    interest = a["debt"]["loan_amount"] * a["debt"]["interest_rate"]
    total_costs = total_opex + fnb_cogs + depreciation + interest
    annual_hours_sold = hours * days

    # Pull key cost buckets from OPEX_BUDGET dynamically
    opex_lookup = {name: amt for name, _, amt in OPEX_BUDGET}
    labor_cost = (opex_lookup.get("Part-Time Wages", 0)
                  + opex_lookup.get("Owner Salary", 0)
                  + opex_lookup.get("Payroll Taxes and Benefits", 0))
    rent_cost = opex_lookup.get("Rent and CAM", 0)

    # Equipment costs
    total_startup = calc_total_startup_costs()
    equipment_cost = total_startup  # simplified

    # Unit metrics
    metrics = {}

    # --- Revenue Metrics ---
    metrics["Revenue Drivers"] = [
        {
            "Metric": "Revenue per Station per Day",
            "Value": total_rev / (stations * days),
            "Unit": "$",
            "Formula": "Total Revenue ÷ (Stations × Days)",
            "Explanation": "How much each gaming station generates daily. Key capacity metric.",
        },
        {
            "Metric": "Revenue per Device-Hour Sold",
            "Value": gaming_rev / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "Gaming Revenue ÷ Annual Hours Sold",
            "Explanation": "Effective hourly rate after accounting for all hours sold.",
        },
        {
            "Metric": "Revenue per Operating Hour",
            "Value": total_rev / (op_hours * days),
            "Unit": "$",
            "Formula": "Total Revenue ÷ (Operating Hours × Days)",
            "Explanation": "Revenue generated per hour the doors are open.",
        },
        {
            "Metric": "F&B Revenue per Gaming Dollar",
            "Value": fnb_rev / gaming_rev if gaming_rev else 0,
            "Unit": "$",
            "Formula": "F&B Revenue ÷ Gaming Revenue",
            "Explanation": "Ancillary revenue capture rate. Higher = better cross-sell.",
        },
        {
            "Metric": "Daily Revenue (Average)",
            "Value": total_rev / days,
            "Unit": "$",
            "Formula": "Total Revenue ÷ 365",
            "Explanation": "Average daily revenue across the year.",
        },
    ]

    # --- Cost Metrics ---
    metrics["Cost Drivers"] = [
        {
            "Metric": "Total Cost per Device-Hour",
            "Value": total_costs / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "(All Costs) ÷ Annual Hours Sold",
            "Explanation": "Fully loaded cost for each hour sold. Must be below price to profit.",
        },
        {
            "Metric": "OpEx per Device-Hour",
            "Value": total_opex / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "Total OpEx ÷ Annual Hours Sold",
            "Explanation": "Operating cost allocation per unit sold.",
        },
        {
            "Metric": "Fixed Cost per Day",
            "Value": (fixed_opex + depreciation) / days,
            "Unit": "$",
            "Formula": "(Fixed OpEx + Depreciation) ÷ 365",
            "Explanation": "Daily cost regardless of traffic. This is your daily 'nut' to cover.",
        },
        {
            "Metric": "Labor Cost per Device-Hour",
            "Value": labor_cost / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "(Wages + Owner + Payroll Tax) ÷ Hours Sold",
            "Explanation": "People cost per unit of production.",
        },
        {
            "Metric": "Rent per Device-Hour",
            "Value": rent_cost / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "Annual Rent ÷ Hours Sold",
            "Explanation": "Occupancy cost per unit. Drops as utilization increases.",
        },
    ]

    # --- Profitability Metrics ---
    ebitda = gross_profit - total_opex
    pretax = ebitda - depreciation - interest

    metrics["Profitability Drivers"] = [
        {
            "Metric": "Gross Profit per Device-Hour",
            "Value": gross_profit / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "Gross Profit ÷ Hours Sold",
            "Explanation": "Margin per unit before operating expenses.",
        },
        {
            "Metric": "Contribution Margin per Hour",
            "Value": (gaming_rev - variable_opex) / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "(Gaming Rev - Variable Costs) ÷ Hours Sold",
            "Explanation": "Incremental profit from one more hour sold. Key pricing decision input.",
        },
        {
            "Metric": "EBITDA per Station per Month",
            "Value": ebitda / (stations * 12),
            "Unit": "$",
            "Formula": "EBITDA ÷ (Stations × 12)",
            "Explanation": "Monthly cash profit each station contributes.",
        },
        {
            "Metric": "Pre-Tax Income per Device-Hour",
            "Value": pretax / annual_hours_sold if annual_hours_sold else 0,
            "Unit": "$",
            "Formula": "Pre-Tax Income ÷ Hours Sold",
            "Explanation": "Bottom-line profit per unit of activity.",
        },
        {
            "Metric": "Operating Leverage Ratio",
            "Value": fixed_opex / total_opex if total_opex else 0,
            "Unit": "%",
            "Formula": "Fixed Costs ÷ Total Costs",
            "Explanation": "Higher = more leverage. Revenue growth drops more to bottom line.",
        },
    ]

    # --- Capacity & Payback ---
    metrics["Capacity & Payback"] = [
        {
            "Metric": "Utilization Rate",
            "Value": utilization,
            "Unit": "%",
            "Formula": "Daily Hours Sold ÷ Max Daily Hours",
            "Explanation": f"{hours} hrs sold ÷ {max_daily_hours} max = {utilization:.1%}. THE #1 KPI.",
        },
        {
            "Metric": "Idle Hours per Day",
            "Value": max_daily_hours - hours,
            "Unit": "hrs",
            "Formula": "Max Hours - Hours Sold",
            "Explanation": "Unsold capacity = lost revenue opportunity.",
        },
        {
            "Metric": "Revenue per Idle Hour (Opportunity Cost)",
            "Value": price,
            "Unit": "$",
            "Formula": "Price per Hour × 1",
            "Explanation": f"Each idle hour costs ${price:.2f} in lost revenue.",
        },
        {
            "Metric": "Daily Idle Revenue Lost",
            "Value": (max_daily_hours - hours) * price,
            "Unit": "$",
            "Formula": "Idle Hours × Price",
            "Explanation": "Total daily revenue left on the table.",
        },
        {
            "Metric": "Equipment Payback Period",
            "Value": equipment_cost / ebitda * 12 if ebitda > 0 else float('inf'),
            "Unit": "months",
            "Formula": "Total Startup Cost ÷ Annual EBITDA × 12",
            "Explanation": "Months until cumulative EBITDA covers initial investment.",
        },
        {
            "Metric": "Breakeven Daily Hours",
            "Value": (total_opex + fnb_cogs + depreciation + interest) / (price * days) if price * days else 0,
            "Unit": "hrs",
            "Formula": "Total Annual Costs ÷ (Price × 365)",
            "Explanation": "Daily device-hours needed to cover all costs.",
        },
    ]

    return metrics


def build_driver_sensitivity(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> pd.DataFrame:
    """
    Show how each operational driver affects EBITDA.

    Tests: what happens if each driver improves by 10%?
    This helps prioritize which lever to pull.

    CONCEPT: Driver sensitivity is how you answer the interview
    question "what would you focus on to improve profitability?"
    You need to know which drivers have the biggest multiplier.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]
    days = a["capacity"]["days_per_year"]

    def calc_ebitda(h, p, fnb, cogs_pct, opex_mult):
        g_rev = h * p * days
        f_rev = fnb
        t_rev = g_rev + f_rev
        cogs = f_rev * cogs_pct
        gp = t_rev - cogs
        opex = 0
        for name, cat, base in OPEX_BUDGET:
            if name == "Merchant & Card Processing Fees":
                opex += t_rev * a["fees"]["merchant_processing_pct"]
            else:
                opex += base * opex_mult
        return gp - opex

    base_ebitda = calc_ebitda(hours, price, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 1.0)

    drivers = [
        ("Utilization (+10%)", calc_ebitda(hours * 1.10, price, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 1.0)),
        ("Price per Hour (+10%)", calc_ebitda(hours, price * 1.10, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 1.0)),
        ("F&B Revenue (+10%)", calc_ebitda(hours, price, a["fnb"]["year1_revenue"] * 1.10, a["fnb"]["cogs_pct"], 1.0)),
        ("F&B COGS (-10%)", calc_ebitda(hours, price, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"] * 0.90, 1.0)),
        ("All OpEx (-10%)", calc_ebitda(hours, price, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 0.90)),
        ("Utilization (-10%)", calc_ebitda(hours * 0.90, price, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 1.0)),
        ("Price per Hour (-10%)", calc_ebitda(hours, price * 0.90, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 1.0)),
        ("All OpEx (+10%)", calc_ebitda(hours, price, a["fnb"]["year1_revenue"], a["fnb"]["cogs_pct"], 1.10)),
    ]

    rows = []
    for label, new_ebitda in drivers:
        delta = new_ebitda - base_ebitda
        rows.append({
            "Driver": label,
            "Base EBITDA": base_ebitda,
            "New EBITDA": new_ebitda,
            "EBITDA Impact ($)": delta,
            "EBITDA Impact (%)": delta / abs(base_ebitda) if base_ebitda != 0 else 0,
        })

    return pd.DataFrame(rows).set_index("Driver")


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 9: UNIT ECONOMICS & DRIVER-BASED METRICS")
    print("=" * 70)

    metrics = compute_unit_economics()
    for group_name, group_metrics in metrics.items():
        print(f"\n--- {group_name} ---")
        for m in group_metrics:
            if m["Unit"] == "$":
                val_fmt = f"${m['Value']:>10,.2f}"
            elif m["Unit"] == "%":
                val_fmt = f"{m['Value']:>10.1%}"
            elif m["Unit"] == "months":
                val_fmt = f"{m['Value']:>10.1f} mo"
            elif m["Unit"] == "hrs":
                val_fmt = f"{m['Value']:>10.0f} hrs"
            else:
                val_fmt = f"{m['Value']:>10.2f}"
            print(f"  {m['Metric']:40s}  {val_fmt}")

    print("\n--- Driver Sensitivity (±10% each) ---")
    sens = build_driver_sensitivity()
    for driver, row in sens.iterrows():
        print(
            f"  {driver:30s}  "
            f"EBITDA: ${row['New EBITDA']:>10,.0f}  "
            f"Δ: ${row['EBITDA Impact ($)']:>+8,.0f}  "
            f"({row['EBITDA Impact (%)']:>+.1%})"
        )
