"""
MODULE 8: ROLLING FORECAST & FORECAST ACCURACY
=================================================
Gaming Arena, LLC — Rolling Forecast Engine

WHAT THIS FILE TEACHES YOU:
- Rolling forecast workflow (THE core FP&A monthly deliverable)
- Actuals + Reforecast = Latest Estimate (LE)
- Forecast accuracy measurement (MAPE, bias detection)
- Run-rate vs assumption-based reforecasting
- Monthly close simulation with validation

WHY THIS MATTERS FOR FP&A ROLES:
  "Maintain rolling forecasts" appears in nearly every FP&A JD.
  This module shows you can BUILD the workflow, not just update
  a spreadsheet someone else created.

CONCEPT: Rolling Forecast
  At any point during the year, you have:
    - BUDGET: Original annual plan (set at start of year, never changes)
    - ACTUALS: Closed months with real results
    - FORECAST: Updated projection for remaining months
    - LATEST ESTIMATE (LE): Actuals + Forecast = full-year outlook

  The LE replaces the budget as the "best guess" of where you'll land.
  It's updated monthly after each close.
"""

import pandas as pd
import numpy as np
from config import ASSUMPTIONS, OPEX_BUDGET
from variance_analysis import build_monthly_actuals, VARIANCE_SCENARIOS


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# =============================================================================
# MONTHLY BUDGET (straight-line, no seasonality)
# =============================================================================

def build_monthly_budget(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> pd.DataFrame:
    """
    Build a 12-month straight-line budget.

    CONCEPT: Budgets are typically set once per year and don't change.
    Monthly budget = Annual budget / 12 (straight-line allocation).
    Some companies seasonalize the budget, but straight-line is standard
    for new businesses without historical seasonal data.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]
    days_per_month = a["capacity"]["days_per_year"] / 12

    gaming_rev = hours * price * days_per_month
    fnb_rev = a["fnb"]["year1_revenue"] / 12
    total_rev = gaming_rev + fnb_rev
    fnb_cogs = fnb_rev * a["fnb"]["cogs_pct"]
    gross_profit = total_rev - fnb_cogs

    opex = 0
    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            opex += total_rev * a["fees"]["merchant_processing_pct"]
        else:
            opex += base_amount / 12

    depreciation = a["depreciation"]["annual_depreciation"] / 12
    ebitda = gross_profit - opex
    ebit = ebitda - depreciation
    interest = (a["debt"]["loan_amount"] * a["debt"]["interest_rate"]) / 12
    pretax = ebit - interest

    rows = []
    for month in MONTH_NAMES:
        rows.append({
            "Month": month,
            "Revenue": total_rev,
            "Gross Profit": gross_profit,
            "EBITDA": ebitda,
            "Pre-Tax Income": pretax,
        })

    return pd.DataFrame(rows).set_index("Month")


# =============================================================================
# ROLLING FORECAST ENGINE
# =============================================================================

def build_rolling_forecast(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    scenario: str = "Base Case",
    close_through_month: int = 6,
    reforecast_method: str = "run_rate",
) -> pd.DataFrame:
    """
    Build a rolling forecast combining actuals (closed months) with
    a reforecast for remaining months.

    Parameters:
        close_through_month: 1-12, how many months of actuals are closed
        reforecast_method:
            "run_rate" — use YTD average run rate for remaining months
            "budget"   — use original budget for remaining months
            "trending" — apply YTD variance trend to remaining months

    Returns DataFrame with columns:
        Month, Source, Budget, Actual/Forecast, Latest Estimate, Variance

    CONCEPT: The Latest Estimate (LE) is the most important number
    in monthly FP&A reporting. It answers: "Given what we know now,
    where will we end the year?"
    """
    a = ASSUMPTIONS

    # Get full-year monthly actuals (scenario-driven)
    monthly = build_monthly_actuals(
        daily_device_hours=daily_device_hours,
        price_per_hour=price_per_hour,
        scenario=scenario,
    )

    # Get monthly budget
    budget_monthly = build_monthly_budget(
        daily_device_hours=daily_device_hours,
        price_per_hour=price_per_hour,
    )

    # Metrics to forecast
    metrics = ["Revenue", "Gross Profit", "EBITDA", "Pre-Tax Income"]
    actual_map = {
        "Revenue": "Actual Revenue",
        "Gross Profit": "Actual Gross Profit",
        "EBITDA": "Actual EBITDA",
        "Pre-Tax Income": "Actual Pre-Tax",
    }

    rows = []

    for metric in metrics:
        actual_col = actual_map[metric]
        budget_col = metric

        # Compute YTD actuals for run-rate calculation
        ytd_actuals = []
        for i in range(close_through_month):
            month = MONTH_NAMES[i]
            ytd_actuals.append(monthly.loc[month, actual_col])

        ytd_avg = np.mean(ytd_actuals) if ytd_actuals else 0
        ytd_total = sum(ytd_actuals)

        # YTD budget
        ytd_budget_vals = []
        for i in range(close_through_month):
            month = MONTH_NAMES[i]
            ytd_budget_vals.append(budget_monthly.loc[month, budget_col])
        ytd_budget = sum(ytd_budget_vals)

        # Variance trend (actual/budget ratio)
        if ytd_budget != 0:
            variance_ratio = ytd_total / ytd_budget
        else:
            variance_ratio = 1.0

        for i, month in enumerate(MONTH_NAMES):
            budget_val = budget_monthly.loc[month, budget_col]

            if i < close_through_month:
                # Closed month — use actuals
                actual_val = monthly.loc[month, actual_col]
                source = "Actual"
                le_val = actual_val
            else:
                # Open month — reforecast
                source = "Forecast"
                if reforecast_method == "run_rate":
                    actual_val = ytd_avg
                elif reforecast_method == "trending":
                    actual_val = budget_val * variance_ratio
                else:  # "budget"
                    actual_val = budget_val
                le_val = actual_val

            rows.append({
                "Month": month,
                "Metric": metric,
                "Source": source,
                "Budget": budget_val,
                "Actual/Forecast": le_val,
                "Variance ($)": le_val - budget_val,
                "Variance (%)": (le_val - budget_val) / abs(budget_val) if budget_val != 0 else 0,
            })

    df = pd.DataFrame(rows)
    return df


def summarize_latest_estimate(forecast_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize rolling forecast into annual totals:
    Full-Year Budget vs Latest Estimate vs Variance.

    CONCEPT: This is the summary table that goes on page 1 of every
    monthly financial review deck.
    """
    summary_rows = []

    for metric in forecast_df["Metric"].unique():
        metric_df = forecast_df[forecast_df["Metric"] == metric]
        budget_total = metric_df["Budget"].sum()
        le_total = metric_df["Actual/Forecast"].sum()
        var_dollar = le_total - budget_total
        var_pct = var_dollar / abs(budget_total) if budget_total != 0 else 0

        # Split into actuals vs forecast portions
        actual_total = metric_df[metric_df["Source"] == "Actual"]["Actual/Forecast"].sum()
        forecast_total = metric_df[metric_df["Source"] == "Forecast"]["Actual/Forecast"].sum()

        summary_rows.append({
            "Metric": metric,
            "Full-Year Budget": budget_total,
            "YTD Actual": actual_total,
            "Remaining Forecast": forecast_total,
            "Latest Estimate": le_total,
            "Variance ($)": var_dollar,
            "Variance (%)": var_pct,
        })

    return pd.DataFrame(summary_rows).set_index("Metric")


# =============================================================================
# FORECAST ACCURACY & BIAS DETECTION
# =============================================================================

def compute_forecast_accuracy(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    scenario: str = "Base Case",
) -> pd.DataFrame:
    """
    Compare budget forecast vs actuals for each month.
    Compute accuracy metrics: error, absolute error, percentage error.

    CONCEPT: Forecast accuracy measurement tells you how good your
    planning process is. High MAPE (>15%) means your assumptions
    need rework. Consistent directional bias means systematic issues.

    Metrics:
    - Error = Actual - Budget (positive = beat forecast)
    - APE = |Error| / |Budget| (absolute percentage error)
    - MAPE = mean of APE across all months
    - Bias = mean of Error (positive = systematically under-forecasting)
    """
    monthly = build_monthly_actuals(
        daily_device_hours=daily_device_hours,
        price_per_hour=price_per_hour,
        scenario=scenario,
    )

    budget = build_monthly_budget(
        daily_device_hours=daily_device_hours,
        price_per_hour=price_per_hour,
    )

    accuracy_metrics = {
        "Revenue": ("Actual Revenue", "Revenue"),
        "EBITDA": ("Actual EBITDA", "EBITDA"),
        "Pre-Tax": ("Actual Pre-Tax", "Pre-Tax Income"),
    }

    rows = []
    for month in MONTH_NAMES:
        for metric_label, (actual_col, budget_col) in accuracy_metrics.items():
            actual = monthly.loc[month, actual_col]
            bgt = budget.loc[month, budget_col]
            error = actual - bgt
            ape = abs(error) / abs(bgt) if bgt != 0 else 0
            direction = "Over" if error > 0 else "Under" if error < 0 else "On Target"

            rows.append({
                "Month": month,
                "Metric": metric_label,
                "Budget": bgt,
                "Actual": actual,
                "Error ($)": error,
                "APE": ape,
                "Direction": direction,
            })

    return pd.DataFrame(rows)


def summarize_forecast_accuracy(accuracy_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute summary accuracy stats per metric: MAPE, bias, hit rate.

    CONCEPT:
    - MAPE < 5%: Excellent forecasting
    - MAPE 5-10%: Good
    - MAPE 10-20%: Needs improvement
    - MAPE > 20%: Forecasting process is broken

    - Bias > 0: Systematically under-forecasting (actuals beat budget)
    - Bias < 0: Systematically over-forecasting (actuals miss budget)
    """
    summary = []

    for metric in accuracy_df["Metric"].unique():
        mdf = accuracy_df[accuracy_df["Metric"] == metric]
        mape = mdf["APE"].mean()
        bias = mdf["Error ($)"].mean()
        bias_pct = mdf["Error ($)"].sum() / abs(mdf["Budget"].sum()) if mdf["Budget"].sum() != 0 else 0
        hit_rate = (mdf["APE"] <= 0.05).mean()  # % of months within 5%
        max_miss = mdf["APE"].max()
        worst_month = mdf.loc[mdf["APE"].idxmax(), "Month"]

        if mape <= 0.05:
            grade = "Excellent"
        elif mape <= 0.10:
            grade = "Good"
        elif mape <= 0.20:
            grade = "Needs Work"
        else:
            grade = "Poor"

        if bias > 0:
            bias_direction = "Under-forecast (conservative)"
        elif bias < 0:
            bias_direction = "Over-forecast (optimistic)"
        else:
            bias_direction = "Neutral"

        summary.append({
            "Metric": metric,
            "MAPE": mape,
            "Grade": grade,
            "Avg Bias ($)": bias,
            "Bias (%)": bias_pct,
            "Bias Direction": bias_direction,
            "Hit Rate (±5%)": hit_rate,
            "Worst Month": worst_month,
            "Worst Miss": max_miss,
        })

    return pd.DataFrame(summary).set_index("Metric")


# =============================================================================
# MONTHLY CLOSE VALIDATION
# =============================================================================

def validate_monthly_close(actuals_month: dict) -> list:
    """
    Run validation checks on monthly actual data before closing.

    CONCEPT: Data validation prevents garbage-in-garbage-out.
    In real FP&A, you run these checks before accepting actuals
    from the GL/ERP system. Flagging anomalies early prevents
    cascading errors in variance reports and forecasts.

    Returns list of validation results (warnings/errors).
    """
    checks = []

    # Check 1: Revenue must be positive
    if actuals_month.get("revenue", 0) < 0:
        checks.append({"Level": "ERROR", "Check": "Revenue is negative", "Detail": f"${actuals_month['revenue']:,.0f}"})
    elif actuals_month.get("revenue", 0) == 0:
        checks.append({"Level": "WARNING", "Check": "Revenue is zero", "Detail": "Confirm this is correct"})
    else:
        checks.append({"Level": "PASS", "Check": "Revenue positive", "Detail": f"${actuals_month['revenue']:,.0f}"})

    # Check 2: COGS should not exceed revenue
    if actuals_month.get("cogs", 0) > actuals_month.get("revenue", 0):
        checks.append({"Level": "ERROR", "Check": "COGS exceeds revenue", "Detail": "Negative gross margin"})
    else:
        checks.append({"Level": "PASS", "Check": "COGS within revenue", "Detail": "Gross margin positive"})

    # Check 3: OpEx reasonability (within 50% of monthly budget)
    a = ASSUMPTIONS
    monthly_opex_budget = sum(amt for _, _, amt in OPEX_BUDGET) / 12
    opex_actual = actuals_month.get("opex", 0)
    opex_ratio = opex_actual / monthly_opex_budget if monthly_opex_budget else 0
    if opex_ratio > 1.50:
        checks.append({"Level": "WARNING", "Check": "OpEx > 150% of budget", "Detail": f"{opex_ratio:.0%} of monthly budget"})
    elif opex_ratio < 0.50:
        checks.append({"Level": "WARNING", "Check": "OpEx < 50% of budget", "Detail": f"{opex_ratio:.0%} — possible missing accruals"})
    else:
        checks.append({"Level": "PASS", "Check": "OpEx within range", "Detail": f"{opex_ratio:.0%} of monthly budget"})

    # Check 4: Hours sold reasonability
    hours = actuals_month.get("hours", 0)
    max_hours = a["capacity"]["total_devices"] * a["capacity"]["operating_hours_per_day"] * 30
    if hours > max_hours:
        checks.append({"Level": "ERROR", "Check": "Hours exceed capacity", "Detail": f"{hours:,.0f} > {max_hours:,.0f} max"})
    elif hours < 0:
        checks.append({"Level": "ERROR", "Check": "Negative hours", "Detail": f"{hours:,.0f}"})
    else:
        utilization = hours / max_hours if max_hours else 0
        checks.append({"Level": "PASS", "Check": "Hours within capacity", "Detail": f"{utilization:.1%} utilization"})

    return checks


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 8: ROLLING FORECAST & FORECAST ACCURACY")
    print("=" * 70)

    # Test rolling forecast (close through June)
    rf = build_rolling_forecast(scenario="Base Case", close_through_month=6)
    print("\n--- Rolling Forecast (Revenue, closed through June) ---")
    rev_rf = rf[rf["Metric"] == "Revenue"]
    for _, row in rev_rf.iterrows():
        src = f"[{row['Source']:8s}]"
        print(
            f"  {row['Month']}  {src}  "
            f"Budget: ${row['Budget']:>8,.0f}  "
            f"LE: ${row['Actual/Forecast']:>8,.0f}  "
            f"Var: ${row['Variance ($)']:>+8,.0f}"
        )

    # Summary
    print("\n--- Latest Estimate Summary ---")
    le_summary = summarize_latest_estimate(rf)
    for metric, row in le_summary.iterrows():
        print(
            f"  {metric:20s}  "
            f"Budget: ${row['Full-Year Budget']:>10,.0f}  "
            f"LE: ${row['Latest Estimate']:>10,.0f}  "
            f"Var: ${row['Variance ($)']:>+10,.0f} ({row['Variance (%)']:>+.1%})"
        )

    # Forecast accuracy
    print("\n--- Forecast Accuracy ---")
    acc = compute_forecast_accuracy(scenario="Base Case")
    acc_summary = summarize_forecast_accuracy(acc)
    for metric, row in acc_summary.iterrows():
        print(
            f"  {metric:12s}  "
            f"MAPE: {row['MAPE']:.1%} [{row['Grade']}]  "
            f"Bias: ${row['Avg Bias ($)']:>+8,.0f}  "
            f"Hit Rate: {row['Hit Rate (±5%)']:.0%}  "
            f"Worst: {row['Worst Month']} ({row['Worst Miss']:.1%})"
        )
