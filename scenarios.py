"""
MODULE 3: SCENARIO & SENSITIVITY ANALYSIS
============================================
Gaming Arena, LLC — Stress-Testing the Model

WHAT THIS FILE TEACHES YOU:
- For loops and nested loops (iterating over combinations)
- numpy basics (numerical computing library)
- Building sensitivity tables (2-variable data tables like Excel)
- Breakeven analysis (goal-seeking in Python)
- How to think about scenario analysis as a finance professional

WHY SCENARIO ANALYSIS MATTERS:
  A single-point forecast is a guess. Scenario analysis shows you:
  1. How bad can it get? (worst case — can you survive?)
  2. What's realistic? (base case — your plan)
  3. What's the upside? (best case — if things go well)
  4. What's the #1 thing that kills you? (sensitivity — where to focus)
"""

import numpy as np
import pandas as pd
from config import ASSUMPTIONS, calc_utilization
from model_engine import build_full_model, build_income_statement


# =============================================================================
# SCENARIO COMPARISON (WORST / BASE / BEST)
# =============================================================================

def run_scenario_comparison() -> pd.DataFrame:
    """
    Run worst, base, and best case models and compare key metrics.

    This mirrors the Scenario Analysis from your SBA packet (Document 04).

    PYTHON CONCEPT: Looping over a list of dictionaries.
    Each scenario is defined by its assumptions, then we run the full model
    for each and collect the results into a comparison table.
    """
    scenarios = [
        {"name": "Worst Case", "daily_hours": 80},
        {"name": "Base Case",  "daily_hours": 100},
        {"name": "Best Case",  "daily_hours": 120},
    ]

    results = {}

    for scenario in scenarios:
        name = scenario["name"]
        hours = scenario["daily_hours"]

        # Run the full 3-statement model with this scenario's utilization
        model = build_full_model(daily_device_hours=hours)
        inc = model["income_statement"]
        cf = model["cash_flow"]
        ratios = model["ratios"]

        # Extract Year 1 metrics for comparison
        results[name] = {
            "Daily Device-Hours": hours,
            "Utilization Rate": calc_utilization(hours),
            "Gaming Revenue": inc.loc["Gaming Revenue", "Year 1"],
            "Total Revenue": inc.loc["Total Revenue", "Year 1"],
            "Gross Profit": inc.loc["Gross Profit", "Year 1"],
            "EBITDA": inc.loc["EBITDA", "Year 1"],
            "EBIT": inc.loc["EBIT (Operating Income)", "Year 1"],
            "Pre-Tax Income": inc.loc["Pre-Tax Income", "Year 1"],
            "Cash from Operations": cf.loc["Net Cash from Operations", "Year 1"],
            "Ending Cash": cf.loc["Ending Cash Balance", "Year 1"],
            "DSCR": ratios.loc["DSCR", "Year 1"],
        }

    return pd.DataFrame(results)


# =============================================================================
# SENSITIVITY TABLE — 2-VARIABLE
# =============================================================================

def build_sensitivity_table(
    metric: str = "EBITDA",
    hours_range: list = None,
    price_range: list = None,
) -> pd.DataFrame:
    """
    Build a 2-variable sensitivity table: device-hours vs. price per hour.

    This is the Python equivalent of Excel's Data Table (What-If Analysis).
    But unlike Excel, you can make it as large as you want and compute instantly.

    Parameters:
        metric: Which metric to show ("EBITDA", "Pre-Tax Income", "DSCR", etc.)
        hours_range: List of daily device-hour values to test
        price_range: List of price-per-hour values to test

    Returns:
        DataFrame where rows = hours, columns = prices, values = metric

    PYTHON CONCEPT: Nested for loops.
    The outer loop iterates over hours, the inner loop over prices.
    We build up results row by row into a 2D grid.
    """
    if hours_range is None:
        hours_range = [60, 70, 80, 90, 100, 110, 120, 130, 140]
    if price_range is None:
        price_range = [7.00, 8.00, 9.00, 10.00, 11.00, 12.00]

    # PYTHON CONCEPT: List comprehension with nested loop
    # This builds the grid efficiently
    table_data = {}

    for price in price_range:
        column_values = []
        for hours in hours_range:
            # Run the income statement for this combination
            inc = build_income_statement(
                daily_device_hours=hours,
                price_per_hour=price,
                forecast_years=1,
            )

            if metric == "DSCR":
                model = build_full_model(
                    daily_device_hours=hours,
                    price_per_hour=price,
                    forecast_years=1,
                )
                value = model["ratios"].loc["DSCR", "Year 1"]
            elif metric in inc.index:
                value = inc.loc[metric, "Year 1"]
            else:
                value = None

            column_values.append(value)

        table_data[f"${price:.0f}/hr"] = column_values

    # Create DataFrame with hours as the index
    df = pd.DataFrame(
        table_data,
        index=[f"{h} hrs/day" for h in hours_range],
    )
    df.index.name = f"{metric} →"
    return df


# =============================================================================
# BREAKEVEN ANALYSIS
# =============================================================================

def find_breakeven_hours(
    target_metric: str = "Pre-Tax Income",
    target_value: float = 0,
    price_per_hour: float = None,
    precision: int = 1,
) -> dict:
    """
    Find the daily device-hours needed to hit a target metric value.

    This is the Python version of Excel's Goal Seek.

    Examples:
      find_breakeven_hours()  →  hours needed for Pre-Tax Income = $0
      find_breakeven_hours("DSCR", 1.25)  →  hours needed for DSCR = 1.25x

    PYTHON CONCEPT: Binary search algorithm.
    Instead of testing every possible value (slow), we use binary search:
      1. Start with a low guess (0) and high guess (480)
      2. Test the midpoint
      3. If too low, search the upper half. If too high, search the lower half.
      4. Repeat until we're close enough.
    This finds the answer in ~20 iterations instead of 480.
    """
    a = ASSUMPTIONS
    price = price_per_hour or a["pricing"]["price_per_hour"]
    max_hours = a["capacity"]["total_devices"] * a["capacity"]["operating_hours_per_day"]

    low, high = 0, max_hours

    # Binary search
    for _ in range(100):  # max iterations (safety net)
        mid = (low + high) / 2

        if target_metric == "DSCR":
            model = build_full_model(
                daily_device_hours=int(mid),
                price_per_hour=price,
                forecast_years=1,
            )
            current_value = model["ratios"].loc["DSCR", "Year 1"]
        else:
            inc = build_income_statement(
                daily_device_hours=int(mid),
                price_per_hour=price,
                forecast_years=1,
            )
            current_value = inc.loc[target_metric, "Year 1"]

        if abs(current_value - target_value) < precision:
            break

        if current_value < target_value:
            low = mid
        else:
            high = mid

    breakeven_hours = round(mid)

    return {
        "metric": target_metric,
        "target_value": target_value,
        "breakeven_daily_hours": breakeven_hours,
        "utilization_at_breakeven": calc_utilization(breakeven_hours),
        "actual_metric_value": current_value,
        "price_per_hour": price,
    }


# =============================================================================
# MONTE CARLO SIMULATION
# =============================================================================

def run_monte_carlo(
    n_simulations: int = 1000,
    hours_mean: int = 100,
    hours_std: int = 15,
    price_mean: float = 9.00,
    price_std: float = 0.50,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Run a Monte Carlo simulation on the model.

    Instead of picking 3 scenarios, this generates 1,000 random combinations
    of utilization and pricing, runs the model for each, and shows you
    the distribution of outcomes.

    WHAT YOU LEARN FROM THIS:
    - What's the probability of a loss? (% of simulations where Pre-Tax < 0)
    - What's the expected EBITDA? (mean across all simulations)
    - What's the worst realistic outcome? (5th percentile)

    PYTHON CONCEPT: numpy random number generation.
    np.random.normal(mean, std, n) generates n random numbers from a
    bell curve centered at `mean` with spread `std`.

    PYTHON CONCEPT: Setting a seed for reproducibility.
    np.random.seed(42) means you get the SAME random numbers every time.
    This is critical for auditable analysis — someone else can reproduce your results.
    """
    rng = np.random.default_rng(seed)

    # Generate random inputs
    # PYTHON CONCEPT: numpy arrays — vectorized operations on many values at once
    hours_samples = rng.normal(hours_mean, hours_std, n_simulations)
    hours_samples = np.clip(hours_samples, 20, 400).astype(int)  # clip to reasonable range

    price_samples = rng.normal(price_mean, price_std, n_simulations)
    price_samples = np.clip(price_samples, 5.0, 15.0)  # clip to reasonable range

    # Run model for each simulation
    # PYTHON CONCEPT: List comprehension — a concise way to build a list
    results = []
    for i in range(n_simulations):
        inc = build_income_statement(
            daily_device_hours=int(hours_samples[i]),
            price_per_hour=float(price_samples[i]),
            forecast_years=1,
        )

        results.append({
            "sim_id": i + 1,
            "daily_hours": int(hours_samples[i]),
            "price_per_hour": float(price_samples[i]),
            "utilization": calc_utilization(int(hours_samples[i])),
            "total_revenue": inc.loc["Total Revenue", "Year 1"],
            "ebitda": inc.loc["EBITDA", "Year 1"],
            "pretax_income": inc.loc["Pre-Tax Income", "Year 1"],
        })

    return pd.DataFrame(results)


def summarize_monte_carlo(sim_df: pd.DataFrame) -> dict:
    """
    Summarize Monte Carlo simulation results.

    Returns key statistics that answer business questions:
    - Expected value (mean) — your best single estimate
    - Standard deviation — how much outcomes vary
    - Percentiles — range of realistic outcomes
    - Probability of loss — risk of Pre-Tax Income < $0
    """
    return {
        "n_simulations": len(sim_df),
        "revenue": {
            "mean": sim_df["total_revenue"].mean(),
            "std": sim_df["total_revenue"].std(),
            "p5": sim_df["total_revenue"].quantile(0.05),
            "p25": sim_df["total_revenue"].quantile(0.25),
            "median": sim_df["total_revenue"].median(),
            "p75": sim_df["total_revenue"].quantile(0.75),
            "p95": sim_df["total_revenue"].quantile(0.95),
        },
        "ebitda": {
            "mean": sim_df["ebitda"].mean(),
            "std": sim_df["ebitda"].std(),
            "p5": sim_df["ebitda"].quantile(0.05),
            "median": sim_df["ebitda"].median(),
            "p95": sim_df["ebitda"].quantile(0.95),
        },
        "pretax_income": {
            "mean": sim_df["pretax_income"].mean(),
            "std": sim_df["pretax_income"].std(),
            "p5": sim_df["pretax_income"].quantile(0.05),
            "median": sim_df["pretax_income"].median(),
            "p95": sim_df["pretax_income"].quantile(0.95),
        },
        "probability_of_loss": (sim_df["pretax_income"] < 0).mean(),
        "probability_dscr_below_125": None,  # Would need DSCR in sim; placeholder
    }


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GAMING ARENA — SCENARIO & SENSITIVITY ANALYSIS")
    print("=" * 70)

    # --- Scenario Comparison ---
    print("\nSCENARIO COMPARISON (Year 1)")
    print("-" * 70)
    comparison = run_scenario_comparison()
    for idx, row in comparison.iterrows():
        if "Rate" in idx or "Utilization" in idx:
            vals = "  ".join(f"{v:>14.1%}" for v in row)
        elif "DSCR" in idx:
            vals = "  ".join(f"{v:>13.2f}x" for v in row)
        elif "Hours" in idx:
            vals = "  ".join(f"{v:>14.0f}" for v in row)
        else:
            vals = "  ".join(f"${v:>13,.0f}" for v in row)
        print(f"  {idx:<26s} {vals}")

    # --- Breakeven ---
    print("\n\nBREAKEVEN ANALYSIS")
    print("-" * 70)
    be_pretax = find_breakeven_hours("Pre-Tax Income", 0)
    print(f"  Break-even (Pre-Tax = $0):")
    print(f"    Daily device-hours needed: {be_pretax['breakeven_daily_hours']}")
    print(f"    Utilization at breakeven:  {be_pretax['utilization_at_breakeven']:.1%}")

    be_dscr = find_breakeven_hours("DSCR", 1.25)
    print(f"\n  SBA Minimum (DSCR = 1.25x):")
    print(f"    Daily device-hours needed: {be_dscr['breakeven_daily_hours']}")
    print(f"    Utilization at breakeven:  {be_dscr['utilization_at_breakeven']:.1%}")

    # --- Sensitivity Table ---
    print("\n\nSENSITIVITY TABLE — EBITDA (Hours x Price)")
    print("-" * 70)
    sens = build_sensitivity_table("EBITDA")
    # Format for display
    formatted = sens.map(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")
    print(formatted.to_string())

    # --- Monte Carlo ---
    print("\n\nMONTE CARLO SIMULATION (1,000 runs)")
    print("-" * 70)
    sim_df = run_monte_carlo(n_simulations=1000)
    summary = summarize_monte_carlo(sim_df)

    print(f"  Expected Revenue:       ${summary['revenue']['mean']:>12,.0f}")
    print(f"  Expected EBITDA:        ${summary['ebitda']['mean']:>12,.0f}")
    print(f"  Expected Pre-Tax:       ${summary['pretax_income']['mean']:>12,.0f}")
    print(f"  Probability of Loss:    {summary['probability_of_loss']:>12.1%}")
    print(f"  EBITDA 5th percentile:  ${summary['ebitda']['p5']:>12,.0f}")
    print(f"  EBITDA 95th percentile: ${summary['ebitda']['p95']:>12,.0f}")
