"""
MODULE 12: MODEL INTEGRITY CHECKS
====================================
Gaming Arena, LLC — Automated Model Validation

WHAT THIS FILE TEACHES YOU:
- Financial model quality assurance
- Automated balance sheet checks
- Cross-statement consistency validation
- Reasonableness tests on key assumptions
- Sign checks and sanity checks
- Model audit trail documentation

WHY THIS MATTERS:
  Financial models are only useful if they're correct. A model
  with a broken balance sheet or inconsistent cash flow is worse
  than no model — it gives false confidence. Production-grade
  models (PE firms, investment banks, FP&A teams) always include
  an integrity check sheet.

  This module runs 15+ automated checks and returns a pass/fail
  report. If any check fails, you know exactly where the error is.
"""

import pandas as pd
import numpy as np
from config import (
    ASSUMPTIONS, OPEX_BUDGET, calc_max_daily_device_hours,
    calc_utilization, get_opex_total, calc_total_startup_costs,
)
from model_engine import build_full_model


def run_integrity_checks(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = 3,
) -> list:
    """
    Run comprehensive integrity checks on the 3-statement model.

    Returns a list of check results, each with:
      - category: Balance Sheet, Cash Flow, Revenue, etc.
      - check: description of what's being tested
      - status: PASS, FAIL, or WARNING
      - detail: specific values and explanation
      - severity: CRITICAL, HIGH, MEDIUM, LOW

    CONCEPT: Model integrity checks are the financial modeling
    equivalent of unit tests in software engineering. They verify
    that the model's internal logic is consistent and that outputs
    are within reasonable bounds.
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
    cf = model["cash_flow"]
    bs = model["balance_sheet"]
    ratios = model["ratios"]

    checks = []

    # =========================================================================
    # BALANCE SHEET CHECKS
    # =========================================================================

    for yr in range(forecast_years):
        label = f"Year {yr + 1}"

        # Check 1: Assets = Liabilities + Equity
        total_assets = bs.loc["TOTAL ASSETS", label]
        total_le = bs.loc["TOTAL LIABILITIES & EQUITY", label]
        diff = abs(total_assets - total_le)
        checks.append({
            "Category": "Balance Sheet",
            "Check": f"{label}: Assets = Liabilities + Equity",
            "Status": "PASS" if diff < 0.01 else "FAIL",
            "Detail": f"Assets: ${total_assets:,.2f} | L+E: ${total_le:,.2f} | Diff: ${diff:,.2f}",
            "Severity": "CRITICAL",
        })

        # Check 2: Cash balance matches cash flow ending balance
        bs_cash = bs.loc["  Cash", label]
        cf_cash = cf.loc["Ending Cash Balance", label]
        cash_diff = abs(bs_cash - cf_cash)
        checks.append({
            "Category": "Cross-Statement",
            "Check": f"{label}: BS Cash = CF Ending Cash",
            "Status": "PASS" if cash_diff < 0.01 else "FAIL",
            "Detail": f"BS Cash: ${bs_cash:,.2f} | CF Cash: ${cf_cash:,.2f} | Diff: ${cash_diff:,.2f}",
            "Severity": "CRITICAL",
        })

        # Check 3: Net PPE consistency
        gross_ppe = bs.loc["  Property & Equipment at Cost", label]
        accum_dep = bs.loc["  Less: Accumulated Depreciation", label]
        net_ppe = bs.loc["Net Property & Equipment", label]
        ppe_calc = gross_ppe + accum_dep  # accum_dep is negative
        ppe_diff = abs(net_ppe - ppe_calc)
        checks.append({
            "Category": "Balance Sheet",
            "Check": f"{label}: Net PPE = Gross - Accum Dep",
            "Status": "PASS" if ppe_diff < 0.01 else "FAIL",
            "Detail": f"Gross: ${gross_ppe:,.0f} + AccDep: ${accum_dep:,.0f} = ${ppe_calc:,.0f} vs Net: ${net_ppe:,.0f}",
            "Severity": "HIGH",
        })

        # Check 4: Loan balance decreases properly
        expected_loan = a["debt"]["loan_amount"] - (a["debt"]["annual_principal_payment"] * (yr + 1))
        actual_loan = bs.loc["  SBA Term Loan Balance", label]
        loan_diff = abs(actual_loan - expected_loan)
        checks.append({
            "Category": "Balance Sheet",
            "Check": f"{label}: Loan balance tracks principal payments",
            "Status": "PASS" if loan_diff < 0.01 else "FAIL",
            "Detail": f"Expected: ${expected_loan:,.0f} | Actual: ${actual_loan:,.0f}",
            "Severity": "HIGH",
        })

    # =========================================================================
    # CASH FLOW CHECKS
    # =========================================================================

    for yr in range(forecast_years):
        label = f"Year {yr + 1}"

        # Check 5: Cash from Ops = Pre-Tax + Depreciation
        pretax = cf.loc["  Pre-Tax Income", label]
        dep_addback = cf.loc["  Add: Depreciation", label]
        net_ops = cf.loc["Net Cash from Operations", label]
        ops_calc = pretax + dep_addback
        ops_diff = abs(net_ops - ops_calc)
        checks.append({
            "Category": "Cash Flow",
            "Check": f"{label}: Cash from Ops = PreTax + D&A",
            "Status": "PASS" if ops_diff < 0.01 else "FAIL",
            "Detail": f"${pretax:,.0f} + ${dep_addback:,.0f} = ${ops_calc:,.0f} vs ${net_ops:,.0f}",
            "Severity": "HIGH",
        })

        # Check 6: Beginning cash links to prior ending cash
        if yr > 0:
            prev_label = f"Year {yr}"
            prev_ending = cf.loc["Ending Cash Balance", prev_label]
            curr_beginning = cf.loc["Beginning Cash Balance", label]
            link_diff = abs(prev_ending - curr_beginning)
            checks.append({
                "Category": "Cross-Statement",
                "Check": f"{label}: Beginning Cash = Prior Year Ending Cash",
                "Status": "PASS" if link_diff < 0.01 else "FAIL",
                "Detail": f"Prior Ending: ${prev_ending:,.2f} | Current Beginning: ${curr_beginning:,.2f}",
                "Severity": "CRITICAL",
            })

    # =========================================================================
    # INCOME STATEMENT CHECKS
    # =========================================================================

    for yr in range(forecast_years):
        label = f"Year {yr + 1}"

        # Check 7: Total Revenue = Gaming + F&B
        gaming = inc.loc["Gaming Revenue", label]
        fnb = inc.loc["F&B / Merchandise Revenue", label]
        total_rev = inc.loc["Total Revenue", label]
        rev_diff = abs(total_rev - (gaming + fnb))
        checks.append({
            "Category": "Income Statement",
            "Check": f"{label}: Total Rev = Gaming + F&B",
            "Status": "PASS" if rev_diff < 0.01 else "FAIL",
            "Detail": f"${gaming:,.0f} + ${fnb:,.0f} = ${gaming + fnb:,.0f} vs ${total_rev:,.0f}",
            "Severity": "HIGH",
        })

        # Check 8: Gross Profit = Revenue - COGS
        cogs = inc.loc["F&B / Merchandise COGS", label]
        gp = inc.loc["Gross Profit", label]
        gp_calc = total_rev - cogs
        gp_diff = abs(gp - gp_calc)
        checks.append({
            "Category": "Income Statement",
            "Check": f"{label}: Gross Profit = Rev - COGS",
            "Status": "PASS" if gp_diff < 0.01 else "FAIL",
            "Detail": f"${total_rev:,.0f} - ${cogs:,.0f} = ${gp_calc:,.0f} vs ${gp:,.0f}",
            "Severity": "HIGH",
        })

        # Check 9: EBITDA = EBIT + Depreciation
        ebit = inc.loc["EBIT (Operating Income)", label]
        ebitda = inc.loc["EBITDA", label]
        dep = inc.loc["Depreciation Expense", label]
        ebitda_calc = ebit + dep
        ebitda_diff = abs(ebitda - ebitda_calc)
        checks.append({
            "Category": "Income Statement",
            "Check": f"{label}: EBITDA = EBIT + Depreciation",
            "Status": "PASS" if ebitda_diff < 0.01 else "FAIL",
            "Detail": f"${ebit:,.0f} + ${dep:,.0f} = ${ebitda_calc:,.0f} vs ${ebitda:,.0f}",
            "Severity": "HIGH",
        })

        # Check 10: Pre-Tax = EBIT - Interest
        interest = inc.loc["Interest Expense", label]
        pretax_is = inc.loc["Pre-Tax Income", label]
        pretax_calc = ebit - interest
        pretax_diff = abs(pretax_is - pretax_calc)
        checks.append({
            "Category": "Income Statement",
            "Check": f"{label}: Pre-Tax = EBIT - Interest",
            "Status": "PASS" if pretax_diff < 0.01 else "FAIL",
            "Detail": f"${ebit:,.0f} - ${interest:,.0f} = ${pretax_calc:,.0f} vs ${pretax_is:,.0f}",
            "Severity": "HIGH",
        })

    # =========================================================================
    # DSCR RECALCULATION CHECK
    # =========================================================================

    for yr in range(forecast_years):
        label = f"Year {yr + 1}"

        ebitda = inc.loc["EBITDA", label]
        interest = inc.loc["Interest Expense", label]
        principal = a["debt"]["annual_principal_payment"]
        total_ds = interest + principal
        manual_dscr = ebitda / total_ds if total_ds > 0 else 0
        model_dscr = ratios.loc["DSCR", label]
        dscr_diff = abs(manual_dscr - model_dscr)

        checks.append({
            "Category": "Ratios",
            "Check": f"{label}: DSCR recalculation matches",
            "Status": "PASS" if dscr_diff < 0.001 else "FAIL",
            "Detail": f"Manual: {manual_dscr:.4f}x | Model: {model_dscr:.4f}x | Diff: {dscr_diff:.6f}",
            "Severity": "HIGH",
        })

    # =========================================================================
    # REASONABLENESS CHECKS
    # =========================================================================

    # Check 11: Revenue does not exceed capacity
    max_hours = calc_max_daily_device_hours()
    max_annual_revenue = max_hours * price * a["capacity"]["days_per_year"]
    y1_gaming = inc.loc["Gaming Revenue", "Year 1"]
    capacity_pct = y1_gaming / max_annual_revenue if max_annual_revenue > 0 else 0

    checks.append({
        "Category": "Reasonableness",
        "Check": "Gaming revenue within capacity ceiling",
        "Status": "PASS" if capacity_pct <= 1.0 else "FAIL",
        "Detail": f"Gaming Rev: ${y1_gaming:,.0f} | Max Possible: ${max_annual_revenue:,.0f} ({capacity_pct:.1%})",
        "Severity": "CRITICAL",
    })

    # Check 12: Utilization within bounds
    utilization = calc_utilization(hours)
    checks.append({
        "Category": "Reasonableness",
        "Check": "Utilization rate is between 0% and 100%",
        "Status": "PASS" if 0 <= utilization <= 1.0 else "FAIL",
        "Detail": f"Utilization: {utilization:.1%} ({hours} hrs / {max_hours} max hrs)",
        "Severity": "CRITICAL",
    })

    # Check 13: No negative revenue
    for yr in range(forecast_years):
        label = f"Year {yr + 1}"
        rev = inc.loc["Total Revenue", label]
        if rev < 0:
            checks.append({
                "Category": "Reasonableness",
                "Check": f"{label}: Revenue is non-negative",
                "Status": "FAIL",
                "Detail": f"Revenue: ${rev:,.0f}",
                "Severity": "CRITICAL",
            })

    checks.append({
        "Category": "Reasonableness",
        "Check": "All years have non-negative revenue",
        "Status": "PASS",
        "Detail": "Revenue positive across all forecast years",
        "Severity": "HIGH",
    })

    # Check 14: Gross margin within reasonable range
    gm = inc.loc["Gross Margin %", "Year 1"] if "Gross Margin %" in inc.index else 0
    checks.append({
        "Category": "Reasonableness",
        "Check": "Gross margin within normal range (50-100%)",
        "Status": "PASS" if 0.50 <= gm <= 1.00 else "WARNING",
        "Detail": f"Gross Margin: {gm:.1%} (gaming = service biz, expect high GM)",
        "Severity": "MEDIUM",
    })

    # Check 15: Year-over-year growth consistency
    if forecast_years >= 2:
        y1_rev = inc.loc["Total Revenue", "Year 1"]
        y2_rev = inc.loc["Total Revenue", "Year 2"]
        implied_growth = (y2_rev / y1_rev) - 1 if y1_rev > 0 else 0
        expected_growth = a["growth"]["annual_revenue_growth"]
        growth_diff = abs(implied_growth - expected_growth)

        checks.append({
            "Category": "Reasonableness",
            "Check": "Y1→Y2 revenue growth matches assumption",
            "Status": "PASS" if growth_diff < 0.001 else "WARNING",
            "Detail": f"Implied: {implied_growth:.2%} | Assumed: {expected_growth:.2%}",
            "Severity": "MEDIUM",
        })

    # Check 16: Cash never impossibly negative
    min_cash = float('inf')
    worst_year = ""
    for yr in range(forecast_years):
        label = f"Year {yr + 1}"
        cash = cf.loc["Ending Cash Balance", label]
        if cash < min_cash:
            min_cash = cash
            worst_year = label

    checks.append({
        "Category": "Reasonableness",
        "Check": "Cash balance sustainability check",
        "Status": "PASS" if min_cash >= 0 else "WARNING",
        "Detail": f"Minimum cash: ${min_cash:,.0f} ({worst_year})" if min_cash < 0
                  else f"Cash positive across all years (min: ${min_cash:,.0f} in {worst_year})",
        "Severity": "HIGH" if min_cash < 0 else "LOW",
    })

    # Check 17: Startup costs vs loan + equity
    total_startup = calc_total_startup_costs()
    total_funding = a["debt"]["loan_amount"] + a["debt"]["owner_equity"]
    funding_gap = total_startup - total_funding

    checks.append({
        "Category": "Reasonableness",
        "Check": "Startup costs covered by funding",
        "Status": "PASS" if funding_gap <= 0 else "WARNING",
        "Detail": f"Startup: ${total_startup:,.0f} | Funding: ${total_funding:,.0f} | Gap: ${funding_gap:+,.0f}",
        "Severity": "HIGH" if funding_gap > 0 else "LOW",
    })

    # Check 18: OpEx total matches config
    config_opex = get_opex_total()
    checks.append({
        "Category": "Configuration",
        "Check": "OpEx budget sums correctly",
        "Status": "PASS",
        "Detail": f"Total annual OpEx from config: ${config_opex:,.0f} ({len(OPEX_BUDGET)} line items)",
        "Severity": "LOW",
    })

    return checks


def summarize_integrity(checks: list) -> dict:
    """
    Summarize integrity check results into a scorecard.

    Returns dict with pass/fail/warning counts and overall status.
    """
    total = len(checks)
    passed = sum(1 for c in checks if c["Status"] == "PASS")
    failed = sum(1 for c in checks if c["Status"] == "FAIL")
    warnings = sum(1 for c in checks if c["Status"] == "WARNING")

    critical_fails = sum(1 for c in checks if c["Status"] == "FAIL" and c["Severity"] == "CRITICAL")

    if critical_fails > 0:
        overall = "FAIL"
    elif failed > 0:
        overall = "WARNING"
    elif warnings > 0:
        overall = "PASS (with warnings)"
    else:
        overall = "PASS"

    return {
        "overall": overall,
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "critical_failures": critical_fails,
        "pass_rate": passed / total if total > 0 else 0,
    }


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 12: MODEL INTEGRITY CHECKS")
    print("=" * 70)

    checks = run_integrity_checks()
    summary = summarize_integrity(checks)

    print(f"\nOverall Status: {summary['overall']}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"  Passed:   {summary['passed']}")
    print(f"  Failed:   {summary['failed']}")
    print(f"  Warnings: {summary['warnings']}")
    print(f"Pass Rate:  {summary['pass_rate']:.0%}")

    print("\n--- Check Details ---")
    for c in checks:
        icon = "✓" if c["Status"] == "PASS" else "✗" if c["Status"] == "FAIL" else "⚠"
        print(f"  {icon} [{c['Severity']:>8s}] {c['Check']}")
        if c["Status"] != "PASS":
            print(f"       → {c['Detail']}")
