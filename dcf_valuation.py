"""
MODULE 11: DCF BUSINESS VALUATION
====================================
Gaming Arena, LLC — Discounted Cash Flow Valuation Engine

WHAT THIS FILE TEACHES YOU:
- DCF valuation mechanics (THE core valuation methodology)
- Unlevered Free Cash Flow (UFCF) computation
- WACC calculation and sensitivity
- Terminal value via perpetual growth method
- Enterprise-to-equity bridge
- Sensitivity analysis on WACC and terminal growth

WHY THIS MATTERS:
  DCF answers "what is this business worth?" It's the most
  rigorous valuation methodology because it values a business
  based on its ability to generate future cash flows, not just
  comparables or rules of thumb.

  For an SBA-funded gaming arena, this helps answer:
  - Is the $200K total investment justified by projected cash flows?
  - What return does the owner earn on their $20K equity?
  - At what assumptions does the business become a bad investment?

FORMULA CHAIN:
  EBITDA → NOPAT → UFCF → PV of UFCFs → Terminal Value → EV → Equity Value
"""

import pandas as pd
import numpy as np
from config import ASSUMPTIONS, OPEX_BUDGET
from model_engine import build_full_model


def compute_ufcf(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = 5,
    tax_rate: float = 0.25,
    capex_pct_of_revenue: float = 0.02,
    nwc_pct_of_revenue: float = 0.05,
) -> pd.DataFrame:
    """
    Compute Unlevered Free Cash Flow (UFCF) for each forecast year.

    UFCF = EBITDA × (1 - Tax Rate) + Depreciation × Tax Rate - CapEx - ΔNWC

    Simplified for this model:
      UFCF = NOPAT + Depreciation - CapEx - ΔNWC
      where NOPAT = EBIT × (1 - Tax Rate)

    Parameters:
        tax_rate: Assumed tax rate (default 25%)
        capex_pct_of_revenue: Maintenance CapEx as % of revenue
        nwc_pct_of_revenue: Net Working Capital as % of revenue

    Returns DataFrame with UFCF buildup by year.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]

    model = build_full_model(
        daily_device_hours=hours,
        price_per_hour=price,
        forecast_years=forecast_years,
    )
    inc = model["income_statement"]

    data = {}
    prev_nwc = 0  # Year 0 NWC assumed zero for startup

    for yr in range(forecast_years):
        label = f"Year {yr + 1}"

        revenue = inc.loc["Total Revenue", label]
        ebitda = inc.loc["EBITDA", label]
        ebit = inc.loc["EBIT (Operating Income)", label]
        depreciation = a["depreciation"]["annual_depreciation"]

        # NOPAT = EBIT × (1 - tax rate)
        nopat = ebit * (1 - tax_rate)

        # Depreciation tax shield is already captured in NOPAT
        # UFCF = NOPAT + D&A - CapEx - ΔNWC

        capex = revenue * capex_pct_of_revenue
        nwc = revenue * nwc_pct_of_revenue
        delta_nwc = nwc - prev_nwc

        ufcf = nopat + depreciation - capex - delta_nwc

        data[label] = {
            "Revenue": revenue,
            "EBITDA": ebitda,
            "EBIT": ebit,
            "Tax Rate": tax_rate,
            "NOPAT": nopat,
            "(+) Depreciation": depreciation,
            "(-) CapEx": capex,
            "(-) ΔNWC": delta_nwc,
            "Unlevered Free Cash Flow": ufcf,
        }

        prev_nwc = nwc

    return pd.DataFrame(data)


def build_dcf_valuation(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = 5,
    wacc: float = 0.12,
    terminal_growth_rate: float = 0.02,
    tax_rate: float = 0.25,
    capex_pct_of_revenue: float = 0.02,
    nwc_pct_of_revenue: float = 0.05,
) -> dict:
    """
    Build a complete DCF valuation.

    Steps:
    1. Project UFCF for each forecast year
    2. Discount each year's UFCF at WACC
    3. Compute terminal value via perpetual growth
    4. Sum PV of UFCFs + PV of terminal value = Enterprise Value
    5. Enterprise-to-equity bridge: EV - Net Debt = Equity Value

    Parameters:
        wacc: Weighted average cost of capital (default 12%)
        terminal_growth_rate: Long-run growth rate (default 2%)

    Returns dict with full valuation output.
    """
    a = ASSUMPTIONS

    # Step 1: Compute UFCF schedule
    ufcf_df = compute_ufcf(
        daily_device_hours=daily_device_hours,
        price_per_hour=price_per_hour,
        forecast_years=forecast_years,
        tax_rate=tax_rate,
        capex_pct_of_revenue=capex_pct_of_revenue,
        nwc_pct_of_revenue=nwc_pct_of_revenue,
    )

    ufcf_values = []
    for yr in range(forecast_years):
        label = f"Year {yr + 1}"
        ufcf_values.append(ufcf_df.loc["Unlevered Free Cash Flow", label])

    # Step 2: Discount each UFCF
    discount_factors = [(1 + wacc) ** (yr + 1) for yr in range(forecast_years)]
    pv_ufcfs = [ufcf / df for ufcf, df in zip(ufcf_values, discount_factors)]

    # Step 3: Terminal value (perpetuity growth method)
    terminal_ufcf = ufcf_values[-1] * (1 + terminal_growth_rate)
    terminal_value = terminal_ufcf / (wacc - terminal_growth_rate)
    pv_terminal = terminal_value / discount_factors[-1]

    # Step 4: Enterprise Value
    pv_ufcf_total = sum(pv_ufcfs)
    enterprise_value = pv_ufcf_total + pv_terminal

    # Step 5: Equity bridge
    net_debt = a["debt"]["loan_amount"]  # Year 0 debt balance
    equity_value = enterprise_value - net_debt

    # Investment return metrics
    total_investment = a["debt"]["total_project_cost"]
    owner_equity = a["debt"]["owner_equity"]
    implied_multiple = enterprise_value / ufcf_values[0] if ufcf_values[0] > 0 else float('inf')
    ev_to_ebitda = enterprise_value / ufcf_df.loc["EBITDA", "Year 1"] if ufcf_df.loc["EBITDA", "Year 1"] > 0 else float('inf')
    roi_on_equity = (equity_value - owner_equity) / owner_equity if owner_equity > 0 else 0
    roi_on_total = (enterprise_value - total_investment) / total_investment if total_investment > 0 else 0

    return {
        "ufcf_schedule": ufcf_df,
        "ufcf_values": ufcf_values,
        "discount_factors": discount_factors,
        "pv_ufcfs": pv_ufcfs,
        "pv_ufcf_total": pv_ufcf_total,
        "terminal_ufcf": terminal_ufcf,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "net_debt": net_debt,
        "equity_value": equity_value,
        "assumptions": {
            "wacc": wacc,
            "terminal_growth_rate": terminal_growth_rate,
            "tax_rate": tax_rate,
            "capex_pct": capex_pct_of_revenue,
            "nwc_pct": nwc_pct_of_revenue,
            "forecast_years": forecast_years,
        },
        "metrics": {
            "implied_ufcf_multiple": implied_multiple,
            "ev_to_ebitda": ev_to_ebitda,
            "roi_on_equity": roi_on_equity,
            "roi_on_total_investment": roi_on_total,
            "total_investment": total_investment,
            "owner_equity": owner_equity,
            "tv_as_pct_of_ev": pv_terminal / enterprise_value if enterprise_value > 0 else 0,
        },
    }


def build_dcf_sensitivity(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = 5,
    wacc_range: list = None,
    growth_range: list = None,
    tax_rate: float = 0.25,
) -> pd.DataFrame:
    """
    Build a WACC vs Terminal Growth sensitivity table for equity value.

    This is the standard DCF sensitivity output seen in every
    investment banking pitch book and equity research report.
    """
    if wacc_range is None:
        wacc_range = [0.08, 0.10, 0.12, 0.14, 0.16, 0.18]
    if growth_range is None:
        growth_range = [0.00, 0.01, 0.02, 0.03, 0.04]

    table = {}
    for g in growth_range:
        col_values = []
        for w in wacc_range:
            if w <= g:
                col_values.append(float('inf'))
                continue
            dcf = build_dcf_valuation(
                daily_device_hours=daily_device_hours,
                price_per_hour=price_per_hour,
                forecast_years=forecast_years,
                wacc=w,
                terminal_growth_rate=g,
                tax_rate=tax_rate,
            )
            col_values.append(dcf["equity_value"])

        table[f"g={g:.0%}"] = col_values

    df = pd.DataFrame(table, index=[f"WACC={w:.0%}" for w in wacc_range])
    df.index.name = "Equity Value →"
    return df


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 11: DCF BUSINESS VALUATION")
    print("=" * 70)

    dcf = build_dcf_valuation()

    print("\n--- UFCF Schedule ---")
    ufcf = dcf["ufcf_schedule"]
    for idx in ufcf.index:
        vals = "  ".join(
            f"${ufcf.loc[idx, c]:>10,.0f}" if isinstance(ufcf.loc[idx, c], (int, float)) and abs(ufcf.loc[idx, c]) > 1
            else f"{ufcf.loc[idx, c]:>10.1%}" if isinstance(ufcf.loc[idx, c], float) and abs(ufcf.loc[idx, c]) <= 1
            else ""
            for c in ufcf.columns
        )
        print(f"  {idx:30s} {vals}")

    print("\n--- DCF Valuation ---")
    print(f"  PV of UFCFs:         ${dcf['pv_ufcf_total']:>12,.0f}")
    print(f"  PV of Terminal Value: ${dcf['pv_terminal']:>12,.0f}")
    print(f"  Enterprise Value:    ${dcf['enterprise_value']:>12,.0f}")
    print(f"  Less: Net Debt:      ${dcf['net_debt']:>12,.0f}")
    print(f"  Equity Value:        ${dcf['equity_value']:>12,.0f}")

    print(f"\n  Implied EV/EBITDA:   {dcf['metrics']['ev_to_ebitda']:.1f}x")
    print(f"  ROI on Equity:       {dcf['metrics']['roi_on_equity']:.1%}")
    print(f"  ROI on Total Inv:    {dcf['metrics']['roi_on_total_investment']:.1%}")
    print(f"  TV as % of EV:       {dcf['metrics']['tv_as_pct_of_ev']:.1%}")

    print("\n--- Sensitivity Table (Equity Value) ---")
    sens = build_dcf_sensitivity()
    formatted = sens.map(lambda x: f"${x:>10,.0f}" if x != float('inf') else "N/A")
    print(formatted.to_string())
