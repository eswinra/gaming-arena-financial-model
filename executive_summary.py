"""
MODULE 10: EXECUTIVE SUMMARY & DATA STORYTELLING
===================================================
Gaming Arena, LLC — Automated Executive Summary Generator

WHAT THIS FILE TEACHES YOU:
- Translating financial data into executive-ready narratives
- Traffic-light (RAG) status summarization
- Risk identification and prioritization
- Recommendation generation based on financial data
- Board-ready communication format

WHY THIS MATTERS:
  The #1 complaint about finance teams is "they show us numbers
  but don't tell us what they mean." Auto-generating narrative
  summaries that highlight what matters, what's at risk, and
  what to do about it is the skill that separates senior analysts
  from junior ones, and CFOs from accountants.

  This module turns your model output into a one-page briefing
  a CEO or board member can read in 2 minutes.
"""

import pandas as pd
import numpy as np
from config import ASSUMPTIONS, OPEX_BUDGET
from model_engine import build_full_model
from variance_analysis import (
    build_budget, build_actuals, compute_variance,
    build_kpi_scorecard, VARIANCE_SCENARIOS,
)


def _rag_status(actual, target, higher_is_better=True, amber_pct=0.05, red_pct=0.15):
    """Determine RAG status for a metric."""
    if target == 0:
        return "GREEN"
    var_pct = (actual - target) / abs(target)
    perf = var_pct if higher_is_better else -var_pct
    if perf >= -amber_pct:
        return "GREEN"
    elif perf >= -red_pct:
        return "AMBER"
    else:
        return "RED"


def generate_executive_summary(
    daily_device_hours: int = None,
    price_per_hour: float = None,
    forecast_years: int = 3,
    scenario: str = "Base Case",
) -> dict:
    """
    Generate a structured executive summary from model outputs.

    Returns a dictionary with:
      - headline: one-sentence summary
      - sections: list of {title, status, narrative} dicts
      - risks: list of identified risks
      - recommendations: list of actionable recommendations
      - model_metadata: assumptions and version info

    CONCEPT: This is a "data storytelling" engine. It reads the
    financial model output and writes the story a human analyst
    would write. The structure follows the standard executive
    briefing format used at companies from startups to Fortune 500.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]
    days = a["capacity"]["days_per_year"]

    # Build model
    model = build_full_model(
        daily_device_hours=hours,
        price_per_hour=price,
        forecast_years=forecast_years,
    )
    inc = model["income_statement"]
    cf = model["cash_flow"]
    ratios = model["ratios"]

    # Build variance data
    budget = build_budget(daily_device_hours=hours, price_per_hour=price)
    actuals = build_actuals(daily_device_hours=hours, price_per_hour=price, scenario=scenario)
    variance = compute_variance(budget, actuals)

    sc_info = VARIANCE_SCENARIOS[scenario]

    # ---- Extract key metrics ----
    y1 = "Year 1"
    total_rev = inc.loc["Total Revenue", y1]
    ebitda = inc.loc["EBITDA", y1]
    ebitda_margin = ebitda / total_rev if total_rev else 0
    pretax = inc.loc["Pre-Tax Income", y1]
    dscr = ratios.loc["DSCR", y1]
    ending_cash = cf.loc["Ending Cash Balance", y1]
    gross_margin = inc.loc["Gross Margin %", y1] if "Gross Margin %" in inc.index else 0

    # Variance metrics
    rev_var = variance.loc["Total Revenue", "Variance ($)"]
    rev_var_pct = variance.loc["Total Revenue", "Variance (%)"]
    ebitda_var = variance.loc["EBITDA", "Variance ($)"]

    # Monthly OpEx for runway
    monthly_opex = sum(amt for _, _, amt in OPEX_BUDGET) / 12
    cash_runway_months = ending_cash / monthly_opex if monthly_opex else 0

    # Loan details
    loan = a["debt"]["loan_amount"]
    interest_rate = a["debt"]["interest_rate"]
    annual_ds = a["debt"]["annual_principal_payment"] + loan * interest_rate

    # Multi-year trend
    last_year = f"Year {forecast_years}"
    rev_last = inc.loc["Total Revenue", last_year]
    ebitda_last = inc.loc["EBITDA", last_year]
    pretax_last = inc.loc["Pre-Tax Income", last_year]
    cash_last = cf.loc["Ending Cash Balance", last_year]

    # ---- Build headline ----
    if pretax > 0 and dscr >= 1.25:
        headline = (
            f"Gaming Arena is projected to generate ${pretax:,.0f} in Year 1 pre-tax income "
            f"with a {dscr:.2f}x DSCR, meeting SBA requirements."
        )
        overall_status = "GREEN"
    elif pretax > 0:
        headline = (
            f"Gaming Arena projects ${pretax:,.0f} pre-tax income but DSCR of {dscr:.2f}x "
            f"is {'below' if dscr < 1.25 else 'near'} the 1.25x SBA minimum."
        )
        overall_status = "AMBER"
    elif ebitda > 0:
        headline = (
            f"Gaming Arena generates positive EBITDA (${ebitda:,.0f}) but "
            f"pre-tax income is negative (${pretax:,.0f}) after debt service."
        )
        overall_status = "AMBER"
    else:
        headline = (
            f"Gaming Arena projects negative EBITDA (${ebitda:,.0f}) and pre-tax loss "
            f"of ${pretax:,.0f} at current assumptions. Model needs revised inputs."
        )
        overall_status = "RED"

    # ---- Build sections ----
    sections = []

    # Revenue
    rev_status = _rag_status(actuals["Total Revenue"], budget["Total Revenue"])
    rev_narrative = (
        f"Year 1 revenue is projected at ${total_rev:,.0f}, driven by "
        f"gaming revenue (${inc.loc['Gaming Revenue', y1]:,.0f}) and "
        f"F&B/merchandise (${inc.loc['F&B / Merchandise Revenue', y1]:,.0f}). "
    )
    if scenario != "Base Case":
        rev_narrative += (
            f"Under the {sc_info['label']} scenario, actual revenue "
            f"{'exceeds' if rev_var >= 0 else 'falls short of'} budget by "
            f"${abs(rev_var):,.0f} ({abs(rev_var_pct):.1%}). "
        )
    rev_narrative += (
        f"Revenue grows to ${rev_last:,.0f} by Year {forecast_years} "
        f"at {a['growth']['annual_revenue_growth']:.1%} annual growth."
    )
    sections.append({"title": "Revenue", "status": rev_status, "narrative": rev_narrative})

    # Profitability
    profit_status = "GREEN" if ebitda_margin > 0.15 else "AMBER" if ebitda_margin > 0 else "RED"
    profit_narrative = (
        f"EBITDA margin is {ebitda_margin:.1%} (${ebitda:,.0f}). "
    )
    if ebitda > 0:
        profit_narrative += (
            f"After depreciation (${a['depreciation']['annual_depreciation']:,.0f}) "
            f"and interest (${loan * interest_rate:,.0f}), "
            f"pre-tax income is ${pretax:,.0f}. "
        )
    else:
        profit_narrative += "The business is not generating positive operating cash flow. "

    # Cost structure — pull from OPEX_BUDGET dynamically
    opex_lookup = {name: amt for name, _, amt in OPEX_BUDGET}
    rent = opex_lookup.get("Rent and CAM", 0)
    wages = (opex_lookup.get("Part-Time Wages", 0)
             + opex_lookup.get("Owner Salary", 0)
             + opex_lookup.get("Payroll Taxes and Benefits", 0))
    profit_narrative += (
        f"Labor costs (${wages:,.0f}) and rent (${rent:,.0f}) represent the two largest "
        f"expense categories at {wages/total_rev:.1%} and {rent/total_rev:.1%} of revenue."
    )
    sections.append({"title": "Profitability", "status": profit_status, "narrative": profit_narrative})

    # Cash & Liquidity
    cash_status = "GREEN" if cash_runway_months > 6 else "AMBER" if cash_runway_months > 3 else "RED"
    cash_narrative = (
        f"Year 1 ending cash balance is ${ending_cash:,.0f}, "
        f"providing approximately {cash_runway_months:.1f} months of operating runway. "
        f"By Year {forecast_years}, cash grows to ${cash_last:,.0f}. "
    )
    if ending_cash < 0:
        cash_narrative += "CRITICAL: Cash balance is negative — additional funding required. "
    sections.append({"title": "Cash & Liquidity", "status": cash_status, "narrative": cash_narrative})

    # Debt Service
    dscr_status = "GREEN" if dscr >= 1.25 else "AMBER" if dscr >= 1.0 else "RED"
    dscr_narrative = (
        f"DSCR is {dscr:.2f}x against the SBA minimum of 1.25x. "
        f"Annual debt service is ${annual_ds:,.0f} "
        f"(${a['debt']['annual_principal_payment']:,.0f} principal + "
        f"${loan * interest_rate:,.0f} interest at {interest_rate:.0%}). "
    )
    if dscr < 1.25:
        dscr_narrative += (
            f"The business does not generate sufficient cash flow to cover debt service "
            f"at current assumptions. DSCR shortfall: {1.25 - dscr:.2f}x."
        )
    elif dscr < 1.50:
        dscr_narrative += "Coverage is adequate but thin — limited margin for underperformance."
    else:
        dscr_narrative += "Strong debt service coverage provides comfortable margin of safety."
    sections.append({"title": "Debt Service", "status": dscr_status, "narrative": dscr_narrative})

    # ---- Identify risks ----
    risks = []

    if dscr < 1.25:
        risks.append({
            "severity": "HIGH",
            "risk": "DSCR below SBA minimum",
            "detail": f"Current DSCR of {dscr:.2f}x is below the 1.25x threshold. Loan approval at risk.",
        })

    utilization = hours / (a["capacity"]["total_devices"] * a["capacity"]["operating_hours_per_day"])
    if utilization < 0.20:
        risks.append({
            "severity": "HIGH",
            "risk": "Low utilization rate",
            "detail": f"At {utilization:.1%} utilization, the business has significant idle capacity.",
        })

    if pretax < 0:
        risks.append({
            "severity": "HIGH",
            "risk": "Negative pre-tax income",
            "detail": f"Year 1 projects a ${abs(pretax):,.0f} loss before taxes.",
        })

    if cash_runway_months < 3:
        risks.append({
            "severity": "HIGH",
            "risk": "Cash runway below 3 months",
            "detail": f"Only {cash_runway_months:.1f} months of runway. Immediate funding action needed.",
        })
    elif cash_runway_months < 6:
        risks.append({
            "severity": "MEDIUM",
            "risk": "Cash runway below 6 months",
            "detail": f"{cash_runway_months:.1f} months of runway. Monitor closely.",
        })

    rent_pct = rent / total_rev
    if rent_pct > 0.25:
        risks.append({
            "severity": "MEDIUM",
            "risk": "High occupancy cost ratio",
            "detail": f"Rent at {rent_pct:.1%} of revenue exceeds 25% threshold for retail businesses.",
        })

    if a["growth"]["annual_revenue_growth"] <= a["growth"]["annual_expense_growth"]:
        risks.append({
            "severity": "LOW",
            "risk": "No margin expansion",
            "detail": (
                f"Revenue growth ({a['growth']['annual_revenue_growth']:.1%}) "
                f"≤ expense growth ({a['growth']['annual_expense_growth']:.1%}). "
                f"Margins will not improve over time."
            ),
        })

    # ---- Generate recommendations ----
    recommendations = []

    if utilization < 0.25:
        target_hours = int(a["capacity"]["total_devices"] * a["capacity"]["operating_hours_per_day"] * 0.25)
        recommendations.append(
            f"Increase utilization from {utilization:.1%} to 25% ({target_hours} daily hours). "
            f"Consider tournaments, group bookings, loyalty programs, and peak/off-peak pricing."
        )

    if dscr < 1.25:
        hours_needed = hours
        while hours_needed < a["capacity"]["total_devices"] * a["capacity"]["operating_hours_per_day"]:
            test_rev = hours_needed * price * days
            test_fnb = a["fnb"]["year1_revenue"]
            test_total = test_rev + test_fnb
            test_cogs = test_fnb * a["fnb"]["cogs_pct"]
            test_gp = test_total - test_cogs
            test_opex = sum(
                test_total * a["fees"]["merchant_processing_pct"] if n == "Merchant & Card Processing Fees" else amt
                for n, _, amt in OPEX_BUDGET
            )
            test_ebitda = test_gp - test_opex
            test_ds = annual_ds
            if test_ebitda / test_ds >= 1.25:
                break
            hours_needed += 1
        if hours_needed < a["capacity"]["total_devices"] * a["capacity"]["operating_hours_per_day"]:
            recommendations.append(
                f"To achieve 1.25x DSCR, increase daily hours from {hours} to {hours_needed} "
                f"({hours_needed / (a['capacity']['total_devices'] * a['capacity']['operating_hours_per_day']):.1%} utilization)."
            )

    if rent_pct > 0.20:
        target_rent = int(total_rev * 0.20)
        recommendations.append(
            f"Negotiate rent reduction from ${rent:,.0f} to ${target_rent:,} "
            f"to bring occupancy cost to 20% of revenue (saves ${rent - target_rent:,.0f}/year)."
        )

    if ebitda > 0 and pretax < 0:
        recommendations.append(
            "Business generates positive EBITDA but debt service consumes operating profit. "
            "Explore loan restructuring: lower rate, extended term, or increased owner equity "
            "to reduce debt service burden."
        )

    if not recommendations:
        recommendations.append(
            "Model assumptions appear viable. Monitor monthly actuals vs budget "
            "and update the rolling forecast quarterly."
        )

    # ---- Model metadata ----
    metadata = {
        "scenario": sc_info["label"],
        "scenario_description": sc_info["description"],
        "daily_hours": hours,
        "price_per_hour": price,
        "forecast_years": forecast_years,
        "utilization": utilization,
        "loan_amount": loan,
        "interest_rate": interest_rate,
    }

    return {
        "headline": headline,
        "overall_status": overall_status,
        "sections": sections,
        "risks": risks,
        "recommendations": recommendations,
        "metadata": metadata,
        "key_metrics": {
            "total_revenue": total_rev,
            "ebitda": ebitda,
            "ebitda_margin": ebitda_margin,
            "pretax_income": pretax,
            "dscr": dscr,
            "ending_cash": ending_cash,
            "cash_runway_months": cash_runway_months,
        },
    }


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 10: EXECUTIVE SUMMARY")
    print("=" * 70)

    for scenario in ["Worst Case", "Base Case", "Best Case"]:
        summary = generate_executive_summary(scenario=scenario)

        print(f"\n{'=' * 70}")
        print(f"SCENARIO: {scenario}")
        print(f"{'=' * 70}")
        print(f"\nHEADLINE [{summary['overall_status']}]:")
        print(f"  {summary['headline']}")

        print("\nSECTIONS:")
        for section in summary["sections"]:
            print(f"\n  [{section['status']:>5s}] {section['title']}")
            # Wrap narrative at ~80 chars
            narrative = section["narrative"]
            words = narrative.split()
            line = "    "
            for word in words:
                if len(line) + len(word) > 78:
                    print(line)
                    line = "    "
                line += word + " "
            if line.strip():
                print(line)

        print("\nRISKS:")
        for risk in summary["risks"]:
            print(f"  [{risk['severity']:>6s}] {risk['risk']}: {risk['detail']}")

        print("\nRECOMMENDATIONS:")
        for i, rec in enumerate(summary["recommendations"], 1):
            print(f"  {i}. {rec}")
