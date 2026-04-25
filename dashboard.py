"""
MODULE 5: INTERACTIVE DASHBOARD
==================================
Gaming Arena, LLC — Streamlit Financial Dashboard

WHAT THIS FILE TEACHES YOU:
- Streamlit framework (build web apps with pure Python — no HTML/CSS/JS)
- Interactive widgets (sliders, dropdowns, inputs)
- Data visualization (charts, metrics, tables)
- How to import and reuse your own modules
- Real-time model recalculation based on user input

HOW TO RUN:
  pip install streamlit pandas numpy openpyxl
  streamlit run dashboard.py

WHAT MAKES THIS DIFFERENT FROM YOUR ORIGINAL DASHBOARD:
  Your original (gaming_arena_budget_dashboard.py) had all the data hardcoded
  inside the dashboard file. This version IMPORTS from the model engine.
  That means:
    1. Change an assumption in config.py → dashboard automatically updates
    2. The same engine powers the Excel export, scenarios, AND the dashboard
    3. No duplicated logic = no inconsistency risk

PYTHON CONCEPT: Separation of concerns.
  config.py       → DATA (assumptions, inputs)
  model_engine.py → LOGIC (calculations, formulas)
  dashboard.py    → PRESENTATION (display, interaction)
  Each file does ONE job. This is how professional software is structured.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Import from your own modules
from config import ASSUMPTIONS, calc_utilization, calc_gaming_revenue, OPEX_BUDGET
from model_engine import build_full_model, build_income_statement
from scenarios import (
    run_scenario_comparison,
    build_sensitivity_table,
    find_breakeven_hours,
    run_monte_carlo,
    summarize_monte_carlo,
)
from variance_analysis import (
    build_budget,
    build_actuals,
    compute_variance,
    build_variance_waterfall,
    generate_variance_commentary,
    build_kpi_scorecard,
    build_monthly_actuals,
    VARIANCE_SCENARIOS,
)
from rolling_forecast import (
    build_rolling_forecast,
    summarize_latest_estimate,
    compute_forecast_accuracy,
    summarize_forecast_accuracy,
)
from unit_economics import compute_unit_economics, build_driver_sensitivity
from executive_summary import generate_executive_summary
from dcf_valuation import build_dcf_valuation, build_dcf_sensitivity
from model_integrity import run_integrity_checks, summarize_integrity
from accounting_engine import (
    get_chart_of_accounts_df,
    get_journal_entries_df,
    build_general_ledger,
    build_trial_balance,
    validate_trial_balance,
    build_fs_mapping,
    build_monthly_gl_summary,
    CHART_OF_ACCOUNTS,
)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
# STREAMLIT CONCEPT: set_page_config must be the FIRST Streamlit command.
# It controls the browser tab title, layout width, and icon.

st.set_page_config(
    page_title="Gaming Arena Financial Model",
    layout="wide",
)

# =============================================================================
# SIDEBAR — USER INPUTS
# =============================================================================
# STREAMLIT CONCEPT: st.sidebar puts widgets in a collapsible left panel.
# These act as model inputs — when the user changes a slider,
# the entire page recalculates automatically.

st.sidebar.header("Model Inputs")
st.sidebar.caption("Adjust assumptions to see real-time model changes")

# Pull defaults from config
a = ASSUMPTIONS

daily_hours = st.sidebar.slider(
    "Daily Device-Hours",
    min_value=40, max_value=200,
    value=a["utilization"]["base_case_hours"],
    step=5,
    help="Average device-hours sold per day. Base case = 100 (20.8% utilization).",
)

price = st.sidebar.slider(
    "Price per Device-Hour ($)",
    min_value=5.0, max_value=15.0,
    value=a["pricing"]["price_per_hour"],
    step=0.50,
    help="Hourly rate charged per gaming station.",
)

forecast_years = st.sidebar.selectbox(
    "Forecast Period",
    options=[1, 2, 3, 4, 5],
    index=2,  # default = 3
    help="Number of years to project.",
)

st.sidebar.divider()
st.sidebar.subheader("Monte Carlo Settings")
mc_sims = st.sidebar.number_input(
    "Simulations",
    min_value=100, max_value=5000, value=1000, step=100,
)

st.sidebar.divider()
st.sidebar.subheader("Variance Analysis")
var_scenario = st.sidebar.selectbox(
    "Actuals Scenario",
    options=["Worst Case", "Base Case", "Best Case"],
    index=1,  # default = Base Case
    help="Select a scenario to compare against budget. Each has specific, defensible assumptions.",
)

st.sidebar.divider()
st.sidebar.subheader("Rolling Forecast")
close_through = st.sidebar.slider(
    "Months Closed",
    min_value=1, max_value=12, value=6, step=1,
    help="How many months of actuals are in. Remaining months are reforecast.",
)
reforecast_method = st.sidebar.selectbox(
    "Reforecast Method",
    options=["run_rate", "budget", "trending"],
    index=0,
    help="run_rate: YTD average. budget: original plan. trending: apply YTD variance ratio.",
)

st.sidebar.divider()
st.sidebar.subheader("DCF Valuation")
dcf_wacc = st.sidebar.slider(
    "WACC (%)",
    min_value=6.0, max_value=20.0, value=12.0, step=0.5,
    help="Weighted average cost of capital. Higher = lower valuation.",
)
dcf_terminal_g = st.sidebar.slider(
    "Terminal Growth (%)",
    min_value=0.0, max_value=5.0, value=2.0, step=0.5,
    help="Long-run perpetual growth rate. Usually 2-3% (GDP growth).",
)
dcf_tax_rate = st.sidebar.slider(
    "Tax Rate (%)",
    min_value=0.0, max_value=40.0, value=25.0, step=1.0,
    help="Assumed income tax rate for NOPAT calculation.",
)

# =============================================================================
# RUN THE MODEL (recalculates every time an input changes)
# =============================================================================
# STREAMLIT CONCEPT: Streamlit re-runs the ENTIRE script from top to bottom
# every time a widget value changes. That's why importing from model_engine
# is efficient — it just recalculates with new inputs.

model = build_full_model(
    daily_device_hours=daily_hours,
    price_per_hour=price,
    forecast_years=forecast_years,
)

inc = model["income_statement"]
cf = model["cash_flow"]
bs = model["balance_sheet"]
ratios = model["ratios"]

# =============================================================================
# HEADER
# =============================================================================
st.title("Gaming Arena — Financial Model Dashboard")
st.caption(
    f"Live model: {daily_hours} device-hrs/day × ${price:.2f}/hr × {forecast_years} years  |  "
    f"Utilization: {calc_utilization(daily_hours):.1%}"
)

# =============================================================================
# KPI CARDS (top row)
# =============================================================================
# STREAMLIT CONCEPT: st.columns creates side-by-side layout.
# st.metric shows a value with optional delta (change indicator).

y1 = "Year 1"

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total Revenue",
    f"${inc.loc['Total Revenue', y1]:,.0f}",
)
col2.metric(
    "EBITDA",
    f"${inc.loc['EBITDA', y1]:,.0f}",
    help="Earnings before interest, taxes, depreciation, and amortization",
)
col3.metric(
    "Pre-Tax Income",
    f"${inc.loc['Pre-Tax Income', y1]:,.0f}",
)
col4.metric(
    "DSCR",
    f"{ratios.loc['DSCR', y1]:.2f}x",
    help="Debt Service Coverage Ratio — SBA minimum is 1.25x",
)
col5.metric(
    "Ending Cash",
    f"${cf.loc['Ending Cash Balance', y1]:,.0f}",
)

st.divider()

# =============================================================================
# TABBED SECTIONS
# =============================================================================

tab13, tab10, tab18, tab1, tab2, tab3, tab4, tab6, tab5, tab7, tab8, tab11, tab12, tab9, tab14, tab15, tab16, tab17 = st.tabs([
    "Executive Summary",
    "Assumptions Lab",
    "Accounting & GL",
    "Income Statement",
    "Cash Flow & Balance Sheet",
    "Scenarios",
    "Sensitivity",
    "Breakeven",
    "Monte Carlo",
    "Variance Analysis",
    "KPI Scorecard",
    "Rolling Forecast",
    "Unit Economics",
    "Cost Drivers",
    "DCF Valuation",
    "Time-Block Revenue",
    "Metrics Reference",
    "Model Integrity",
])

# --- TAB 1: Income Statement ---
with tab1:
    st.subheader("Projected Income Statement")

    # Format the DataFrame for display
    # PYTHON CONCEPT: .map() applies a function to every cell
    display_inc = inc.copy().astype(object)
    for col in display_inc.columns:
        display_inc[col] = display_inc[col].apply(
            lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) and abs(x) > 1
            else f"{x:.1%}" if isinstance(x, float) and abs(x) <= 1
            else "" if pd.isna(x) else str(x)
        )
    st.dataframe(display_inc, use_container_width=True, height=700)

    # Revenue composition chart (matplotlib — avoids pyarrow issues)
    st.subheader("Revenue Composition")
    rev_data = pd.DataFrame({
        "Gaming Revenue": [inc.loc["Gaming Revenue", c] for c in inc.columns],
        "F&B Revenue": [inc.loc["F&B / Merchandise Revenue", c] for c in inc.columns],
    }, index=inc.columns)

    fig_rev, ax_rev = plt.subplots(figsize=(8, 4))
    rev_data.plot(kind="bar", stacked=True, ax=ax_rev, color=["#4e79a7", "#59a14f"])
    ax_rev.set_ylabel("Revenue ($)")
    ax_rev.set_title("Revenue Composition by Year")
    ax_rev.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_rev.legend(loc="upper left")
    plt.tight_layout()
    st.pyplot(fig_rev)
    plt.close(fig_rev)

# --- TAB 2: Cash Flow & Balance Sheet ---
with tab2:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Cash Flow Statement")
        display_cf = cf.copy().astype(object)

        # Mark section headers so they look like titles, not missing data
        section_headers = ["Cash Flow from Operations", "Cash Flow from Financing"]
        for col in display_cf.columns:
            display_cf[col] = display_cf[col].apply(
                lambda x: "" if pd.isna(x)
                else f"${x:,.0f}" if isinstance(x, (int, float))
                else str(x)
            )
        for header in section_headers:
            if header in display_cf.index:
                for col in display_cf.columns:
                    display_cf.loc[header, col] = "----------"
        st.dataframe(display_cf, use_container_width=True)

    with c2:
        st.subheader("Key Ratios")
        display_ratios = ratios.copy().astype(object)
        for idx in display_ratios.index:
            for col in display_ratios.columns:
                val = display_ratios.loc[idx, col]
                if not isinstance(val, (int, float)):
                    display_ratios.loc[idx, col] = ""
                elif "Margin" in idx or "Return" in idx:
                    display_ratios.loc[idx, col] = f"{val:.1%}"
                elif "DSCR" in idx or "Debt" in idx:
                    display_ratios.loc[idx, col] = f"{val:.2f}x"
                elif "Cash Balance" in idx:
                    display_ratios.loc[idx, col] = f"${val:,.0f}"
                elif "Runway" in idx:
                    display_ratios.loc[idx, col] = f"{val:.1f} mo"
                else:
                    display_ratios.loc[idx, col] = f"{val:.2f}"
        st.dataframe(display_ratios, use_container_width=True)

    # Cash balance trend (matplotlib)
    st.subheader("Cash Balance Trend")
    cash_vals = [cf.loc["Ending Cash Balance", c] for c in cf.columns]

    fig_cash, ax_cash = plt.subplots(figsize=(8, 3.5))
    ax_cash.plot(list(cf.columns), cash_vals, marker="o", linewidth=2, color="#4e79a7")
    ax_cash.fill_between(list(cf.columns), cash_vals, alpha=0.15, color="#4e79a7")
    ax_cash.set_ylabel("Cash Balance ($)")
    ax_cash.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_cash.set_title("Ending Cash Balance by Year")
    plt.tight_layout()
    st.pyplot(fig_cash)
    plt.close(fig_cash)

# --- TAB 3: Scenarios ---
with tab3:
    st.subheader("Scenario Comparison — Year 1")
    comparison = run_scenario_comparison()

    # Format for display — row-aware formatting
    display_comp = comparison.copy().astype(object)
    for idx in display_comp.index:
        for col in display_comp.columns:
            val = display_comp.loc[idx, col]
            if not isinstance(val, (int, float)):
                display_comp.loc[idx, col] = str(val)
            elif "Rate" in idx or "Utilization" in idx:
                display_comp.loc[idx, col] = f"{val:.1%}"
            elif "DSCR" in idx:
                display_comp.loc[idx, col] = f"{val:.2f}x"
            elif "Hours" in idx:
                display_comp.loc[idx, col] = f"{val:.0f}"
            else:
                display_comp.loc[idx, col] = f"${val:,.0f}"
    st.dataframe(display_comp, use_container_width=True)

    # Visual comparison (matplotlib)
    st.subheader("EBITDA by Scenario")
    scenarios = list(comparison.columns)
    ebitda_vals = [comparison.loc["EBITDA", c] for c in scenarios]
    bar_colors = ["#e15759" if v < 0 else "#59a14f" for v in ebitda_vals]

    fig_scen, ax_scen = plt.subplots(figsize=(6, 3.5))
    ax_scen.bar(scenarios, ebitda_vals, color=bar_colors)
    ax_scen.set_ylabel("EBITDA ($)")
    ax_scen.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_scen.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax_scen.set_title("Year 1 EBITDA by Scenario")
    plt.tight_layout()
    st.pyplot(fig_scen)
    plt.close(fig_scen)

# --- TAB 4: Sensitivity ---
with tab4:
    st.subheader("EBITDA Sensitivity Table")
    st.caption("How EBITDA changes with different combinations of daily hours and pricing")

    sens = build_sensitivity_table(
        "EBITDA",
        hours_range=[60, 70, 80, 90, 100, 110, 120, 130, 140, 160],
        price_range=[7.00, 8.00, 9.00, 10.00, 11.00, 12.00],
    )

    # Color-code: green if positive, red if negative
    def color_ebitda(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "background-color: #d4edda"
            elif val < 0:
                return "background-color: #f8d7da"
        return ""

    styled_sens = sens.style.map(color_ebitda).format("${:,.0f}")
    st.dataframe(styled_sens, use_container_width=True)

    # Also show DSCR sensitivity
    st.subheader("DSCR Sensitivity Table")
    st.caption("SBA minimum is 1.25x — cells below threshold are flagged red")
    sens_dscr = build_sensitivity_table(
        "DSCR",
        hours_range=[60, 70, 80, 90, 100, 110, 120, 130, 140],
        price_range=[7.00, 8.00, 9.00, 10.00, 11.00, 12.00],
    )

    def color_dscr(val):
        if isinstance(val, (int, float)):
            if val >= 1.25:
                return "background-color: #d4edda"
            else:
                return "background-color: #f8d7da"
        return ""

    styled_dscr = sens_dscr.style.map(color_dscr).format("{:.2f}x")
    st.dataframe(styled_dscr, use_container_width=True)

# --- TAB 5: Monte Carlo ---
with tab5:
    st.subheader("Monte Carlo Simulation")
    st.caption(
        f"Running {mc_sims:,} simulations with random utilization and pricing. "
        f"This shows the distribution of possible outcomes."
    )

    sim_df = run_monte_carlo(n_simulations=mc_sims)
    summary = summarize_monte_carlo(sim_df)

    # Summary metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Expected EBITDA", f"${summary['ebitda']['mean']:,.0f}")
    m2.metric("Probability of Loss", f"{summary['probability_of_loss']:.1%}")
    m3.metric("EBITDA 5th Pctl", f"${summary['ebitda']['p5']:,.0f}")
    m4.metric("EBITDA 95th Pctl", f"${summary['ebitda']['p95']:,.0f}")
    if summary.get("dscr") and summary["dscr"].get("mean") is not None:
        m5.metric("Expected DSCR", f"{summary['dscr']['mean']:.2f}x")
    if summary.get("probability_dscr_below_125") is not None:
        m6.metric("P(DSCR < 1.25x)", f"{summary['probability_dscr_below_125']:.1%}")

    # Distribution chart (matplotlib histogram)
    st.subheader("EBITDA Distribution")
    # PYTHON CONCEPT: Histogram via matplotlib — more reliable than st.bar_chart
    fig_hist, ax_hist = plt.subplots(figsize=(8, 4))
    ax_hist.hist(sim_df["ebitda"], bins=30, color="#4e79a7", edgecolor="white", alpha=0.85)
    ax_hist.axvline(x=0, color="red", linewidth=1, linestyle="--", label="Breakeven")
    ax_hist.axvline(x=sim_df["ebitda"].mean(), color="#59a14f", linewidth=1.5,
                    linestyle="-", label=f"Mean: ${sim_df['ebitda'].mean():,.0f}")
    ax_hist.set_xlabel("EBITDA ($)")
    ax_hist.set_ylabel("Frequency")
    ax_hist.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_hist.legend()
    ax_hist.set_title("Monte Carlo EBITDA Distribution")
    plt.tight_layout()
    st.pyplot(fig_hist)
    plt.close(fig_hist)

    # Scatter: hours vs EBITDA (matplotlib)
    st.subheader("Utilization vs. EBITDA")
    fig_scat, ax_scat = plt.subplots(figsize=(8, 4))
    scatter = ax_scat.scatter(
        sim_df["daily_hours"], sim_df["ebitda"],
        c=sim_df["price_per_hour"], cmap="viridis", alpha=0.4, s=12,
    )
    cbar = fig_scat.colorbar(scatter, ax=ax_scat)
    cbar.set_label("Price/Hour ($)")
    ax_scat.set_xlabel("Daily Device-Hours")
    ax_scat.set_ylabel("EBITDA ($)")
    ax_scat.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_scat.axhline(y=0, color="red", linewidth=0.8, linestyle="--")
    ax_scat.set_title("Utilization vs. EBITDA (colored by price)")
    plt.tight_layout()
    st.pyplot(fig_scat)
    plt.close(fig_scat)

# --- TAB 6: Breakeven ---
with tab6:
    st.subheader("Breakeven Analysis")

    be_col1, be_col2 = st.columns(2)

    with be_col1:
        st.markdown("**Pre-Tax Breakeven (Income = $0)**")
        be_pretax = find_breakeven_hours("Pre-Tax Income", 0, price_per_hour=price)
        st.metric("Daily Hours Needed", f"{be_pretax['breakeven_daily_hours']}")
        st.metric("Utilization at Breakeven", f"{be_pretax['utilization_at_breakeven']:.1%}")
        st.caption(f"At ${price:.2f}/hr pricing")

    with be_col2:
        st.markdown("**SBA Minimum (DSCR = 1.25x)**")
        be_dscr = find_breakeven_hours("DSCR", 1.25, price_per_hour=price)
        st.metric("Daily Hours Needed", f"{be_dscr['breakeven_daily_hours']}")
        st.metric("Utilization at Breakeven", f"{be_dscr['utilization_at_breakeven']:.1%}")
        st.caption(f"At ${price:.2f}/hr pricing")

    # Breakeven across different prices
    st.subheader("Breakeven Hours at Different Price Points")
    be_table = []
    for p in [7.0, 8.0, 9.0, 10.0, 11.0, 12.0]:
        be = find_breakeven_hours("Pre-Tax Income", 0, price_per_hour=p)
        be_table.append({
            "Price/Hour": f"${p:.2f}",
            "Breakeven Hours": be["breakeven_daily_hours"],
            "Utilization": f"{be['utilization_at_breakeven']:.1%}",
        })
    st.dataframe(pd.DataFrame(be_table), use_container_width=True)

# --- TAB 7: Variance Analysis ---
with tab7:
    st.subheader("Budget vs Actual Variance Analysis")

    sc_info = VARIANCE_SCENARIOS[var_scenario]
    st.caption(f"**{sc_info['label']}**: {sc_info['description']}")

    budget = build_budget(daily_device_hours=daily_hours, price_per_hour=price)
    actuals_data = build_actuals(
        daily_device_hours=daily_hours, price_per_hour=price, scenario=var_scenario,
    )
    variance = compute_variance(budget, actuals_data)

    # Variance table with color coding
    st.markdown("**Annual Variance Report**")

    def color_variance_row(row):
        if row["Direction"] == "Favorable":
            return ["background-color: #d4edda"] * len(row)
        elif row["Direction"] == "Unfavorable" and row["Material"]:
            return ["background-color: #f8d7da"] * len(row)
        elif row["Direction"] == "Unfavorable":
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    display_var = variance[["Budget", "Actual", "Variance ($)", "Variance (%)", "Direction", "Material"]].copy()
    styled_var = display_var.style.apply(color_variance_row, axis=1).format({
        "Budget": "${:,.0f}",
        "Actual": "${:,.0f}",
        "Variance ($)": "${:+,.0f}",
        "Variance (%)": "{:+.1%}",
    })
    st.dataframe(styled_var, use_container_width=True, height=600)

    # Waterfall chart
    st.subheader("Variance Waterfall")
    st.caption("What drove the difference between budgeted and actual Pre-Tax Income?")
    waterfall = build_variance_waterfall(variance)

    if not waterfall.empty:
        fig_wf, ax_wf = plt.subplots(figsize=(10, 5))

        drivers = waterfall["Driver"].tolist()
        impacts = waterfall["Impact ($)"].tolist()
        colors = ["#59a14f" if v >= 0 else "#e15759" for v in impacts]

        # Build cumulative bars for waterfall effect
        budget_pretax = variance.loc["Pre-Tax Income", "Budget"]
        bottoms = []
        running = budget_pretax
        for impact in impacts:
            if impact >= 0:
                bottoms.append(running)
            else:
                bottoms.append(running + impact)
            running += impact

        ax_wf.bar(drivers, [abs(v) for v in impacts], bottom=bottoms, color=colors, width=0.6)
        ax_wf.axhline(y=budget_pretax, color="#4e79a7", linewidth=1, linestyle="--",
                       label=f"Budget: ${budget_pretax:,.0f}")
        ax_wf.axhline(y=running, color="#e15759", linewidth=1, linestyle="--",
                       label=f"Actual: ${running:,.0f}")
        ax_wf.set_ylabel("Pre-Tax Income ($)")
        ax_wf.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax_wf.legend(loc="upper right")
        ax_wf.set_title("Pre-Tax Income: Budget to Actual Bridge")
        plt.xticks(rotation=30, ha="right", fontsize=9)
        plt.tight_layout()
        st.pyplot(fig_wf)
        plt.close(fig_wf)

    # Auto-generated commentary
    st.subheader("Variance Commentary")
    commentary = generate_variance_commentary(variance)
    for i, comment in enumerate(commentary, 1):
        st.markdown(f"**{i}.** {comment}")

    # Monthly trend
    st.subheader("Monthly Trend Analysis")
    monthly = build_monthly_actuals(
        daily_device_hours=daily_hours, price_per_hour=price, scenario=var_scenario,
    )

    fig_trend, (ax_rev_t, ax_eb_t) = plt.subplots(1, 2, figsize=(12, 4))

    months = list(monthly.index)
    ax_rev_t.plot(months, monthly["Actual Revenue"], marker="o", label="Actual", color="#4e79a7")
    ax_rev_t.plot(months, monthly["Budget Revenue"], linestyle="--", label="Budget", color="#888780")
    ax_rev_t.set_title("Monthly Revenue: Actual vs Budget")
    ax_rev_t.set_ylabel("Revenue ($)")
    ax_rev_t.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_rev_t.legend(fontsize=8)
    ax_rev_t.tick_params(axis="x", rotation=45)

    ax_eb_t.bar(months, monthly["EBITDA Variance ($)"],
                color=["#59a14f" if v >= 0 else "#e15759" for v in monthly["EBITDA Variance ($)"]])
    ax_eb_t.set_title("Monthly EBITDA Variance ($)")
    ax_eb_t.set_ylabel("Variance ($)")
    ax_eb_t.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_eb_t.axhline(y=0, color="gray", linewidth=0.8)
    ax_eb_t.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    st.pyplot(fig_trend)
    plt.close(fig_trend)

# --- TAB 8: KPI Scorecard ---
with tab8:
    st.subheader("KPI Scorecard")
    st.caption("Red / Amber / Green status against annual targets")

    budget_kpi = build_budget(daily_device_hours=daily_hours, price_per_hour=price)
    actuals_kpi = build_actuals(
        daily_device_hours=daily_hours, price_per_hour=price, scenario=var_scenario,
    )
    scorecard = build_kpi_scorecard(budget_kpi, actuals_kpi)

    # RAG color mapping
    rag_colors = {"GREEN": "#d4edda", "AMBER": "#fff3cd", "RED": "#f8d7da"}
    rag_text = {"GREEN": "#155724", "AMBER": "#856404", "RED": "#721c24"}

    # Display as styled metric cards
    cols_per_row = 4
    for i in range(0, len(scorecard), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(scorecard):
                break
            row = scorecard.iloc[idx]
            rag = row["RAG"]

            # Format values
            if row["Unit"] == "$":
                target_fmt = f"${row['Target']:,.0f}"
                actual_fmt = f"${row['Actual']:,.0f}"
            elif row["Unit"] == "%":
                target_fmt = f"{row['Target']:.1%}"
                actual_fmt = f"{row['Actual']:.1%}"
            else:
                target_fmt = f"{row['Target']:.2f}x"
                actual_fmt = f"{row['Actual']:.2f}x"

            var_fmt = f"{row['Variance (%)']:+.1%}"

            with col:
                st.markdown(
                    f"<div style='background:{rag_colors[rag]};padding:16px;border-radius:8px;"
                    f"border-left:4px solid {rag_text[rag]};margin-bottom:8px;'>"
                    f"<div style='font-size:12px;color:{rag_text[rag]};font-weight:600;'>{row['KPI']}</div>"
                    f"<div style='font-size:24px;font-weight:700;color:{rag_text[rag]};'>{actual_fmt}</div>"
                    f"<div style='font-size:12px;color:{rag_text[rag]};'>Target: {target_fmt}  |  {var_fmt}</div>"
                    f"<div style='font-size:11px;font-weight:600;color:{rag_text[rag]};margin-top:4px;'>{rag}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # Scorecard detail table
    st.subheader("Scorecard Detail")
    def color_rag(val):
        if val == "GREEN":
            return "background-color: #d4edda; color: #155724; font-weight: bold"
        elif val == "AMBER":
            return "background-color: #fff3cd; color: #856404; font-weight: bold"
        elif val == "RED":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold"
        return ""

    # Build a string-typed DataFrame to avoid pandas type errors
    sc_rows = []
    for idx_sc in range(len(scorecard)):
        row = scorecard.iloc[idx_sc]
        unit = row["Unit"]
        if unit == "$":
            t_fmt = f"${row['Target']:,.0f}"
            a_fmt = f"${row['Actual']:,.0f}"
        elif unit == "%":
            t_fmt = f"{row['Target']:.1%}"
            a_fmt = f"{row['Actual']:.1%}"
        else:
            t_fmt = f"{row['Target']:.2f}x"
            a_fmt = f"{row['Actual']:.2f}x"
        sc_rows.append({
            "KPI": row["KPI"],
            "Target": t_fmt,
            "Actual": a_fmt,
            "Variance": f"{row['Variance (%)']:+.1%}",
            "RAG": row["RAG"],
        })
    display_sc = pd.DataFrame(sc_rows)
    styled_sc = display_sc.style.map(color_rag, subset=["RAG"])
    st.dataframe(styled_sc, use_container_width=True, hide_index=True)

    # YTD trend chart
    st.subheader("YTD Revenue Tracking")
    monthly_kpi = build_monthly_actuals(
        daily_device_hours=daily_hours, price_per_hour=price, scenario=var_scenario,
    )

    fig_ytd, ax_ytd = plt.subplots(figsize=(8, 4))
    months_list = list(monthly_kpi.index)
    ax_ytd.plot(months_list, monthly_kpi["YTD Actual Revenue"], marker="o",
                linewidth=2, color="#4e79a7", label="YTD Actual")
    ax_ytd.plot(months_list, monthly_kpi["YTD Budget Revenue"], linestyle="--",
                linewidth=2, color="#888780", label="YTD Budget")
    ax_ytd.fill_between(
        months_list,
        monthly_kpi["YTD Actual Revenue"],
        monthly_kpi["YTD Budget Revenue"],
        alpha=0.15,
        color="#4e79a7",
    )
    ax_ytd.set_ylabel("Cumulative Revenue ($)")
    ax_ytd.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_ytd.set_title("Year-to-Date Revenue: Actual vs Budget")
    ax_ytd.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig_ytd)
    plt.close(fig_ytd)

# --- TAB 9: Cost Drivers ---
with tab9:
    st.subheader("Cost Driver Analysis")
    st.caption(
        "See where your money goes and test how adjusting major expenses affects profitability. "
        "Sliders below let you simulate rent negotiations, staffing changes, and other cost levers."
    )

    y1_rev = inc.loc["Total Revenue", y1]

    # ---- What-If Cost Adjustments (sliders FIRST so chart can use them) ----
    st.markdown("### Adjust Cost Levers")
    st.caption(
        "Drag the sliders to test scenarios like negotiating lower rent, "
        "cutting staff hours, or reducing marketing spend. The chart and metrics update instantly."
    )

    # Define adjustable cost levers with their base amounts and reasonable ranges
    adj_col1, adj_col2, adj_col3 = st.columns(3)

    with adj_col1:
        adj_rent = st.slider(
            "Rent & CAM ($/yr)",
            min_value=48_000, max_value=96_000, value=78_000, step=2_000,
            help="Base: $78,000. A smaller or cheaper space could cut this significantly.",
        )
        adj_wages = st.slider(
            "Part-Time Wages ($/yr)",
            min_value=30_000, max_value=85_000, value=65_700, step=1_000,
            help="Base: $65,700. Fewer shifts or lower headcount reduces this.",
        )

    with adj_col2:
        adj_owner = st.slider(
            "Owner Salary ($/yr)",
            min_value=0, max_value=65_000, value=45_000, step=5_000,
            help="Base: $45,000. Some owners take less in Year 1 to improve cash flow.",
        )
        adj_utilities = st.slider(
            "Utilities & Internet ($/yr)",
            min_value=10_000, max_value=24_000, value=18_000, step=1_000,
            help="Base: $18,000. Energy-efficient equipment or better rates.",
        )

    with adj_col3:
        adj_insurance = st.slider(
            "Insurance ($/yr)",
            min_value=6_000, max_value=18_000, value=12_000, step=1_000,
            help="Base: $12,000. Shop around or adjust coverage levels.",
        )
        adj_marketing = st.slider(
            "Marketing & Advertising ($/yr)",
            min_value=1_000, max_value=12_000, value=6_000, step=500,
            help="Base: $6,000. Organic growth vs paid acquisition tradeoff.",
        )

    # Build adjustments map
    adjustments_map = {
        "Rent and CAM": adj_rent,
        "Owner Salary": adj_owner,
        "Part-Time Wages": adj_wages,
        "Utilities and Internet": adj_utilities,
        "Insurance": adj_insurance,
        "Marketing and Advertising": adj_marketing,
    }

    # Payroll taxes scale proportionally with wages
    wage_ratio = adj_wages / 65_700 if 65_700 > 0 else 1.0
    payroll_tax_base = 13_284
    adj_payroll_tax = payroll_tax_base * wage_ratio

    # ---- Cost breakdown chart (uses slider values) ----
    st.divider()
    y1_opex_items = []
    adjusted_opex = 0
    original_opex = 0

    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            amt = y1_rev * a["fees"]["merchant_processing_pct"]
            original_opex += amt
            adjusted_opex += amt
        elif name == "Payroll Taxes and Benefits":
            original_opex += base_amount
            adjusted_opex += adj_payroll_tax
            amt = adj_payroll_tax
        elif name in adjustments_map:
            original_opex += base_amount
            adjusted_opex += adjustments_map[name]
            amt = adjustments_map[name]
        else:
            original_opex += base_amount
            adjusted_opex += base_amount
            amt = base_amount
        y1_opex_items.append({"Expense": name, "Amount": amt, "Category": category})

    # Add depreciation and interest for full picture
    depreciation = a["depreciation"]["annual_depreciation"]
    interest = a["debt"]["loan_amount"] * a["debt"]["interest_rate"]
    y1_opex_items.append({"Expense": "Depreciation", "Amount": depreciation, "Category": "non-cash"})
    y1_opex_items.append({"Expense": "Interest Expense", "Amount": interest, "Category": "financing"})

    cost_df = pd.DataFrame(y1_opex_items)
    cost_df["% of Revenue"] = cost_df["Amount"] / y1_rev
    cost_df = cost_df.sort_values("Amount", ascending=True)  # ascending for horizontal bar

    # Horizontal bar chart — reflects slider values
    st.markdown("**Year 1 Cost Breakdown (sorted by size — reflects slider adjustments)**")
    fig_cost, ax_cost = plt.subplots(figsize=(9, 5))
    bar_colors = []
    for _, row in cost_df.iterrows():
        if row["Amount"] >= 30_000:
            bar_colors.append("#e15759")   # red = high-impact
        elif row["Amount"] >= 10_000:
            bar_colors.append("#f28e2b")   # orange = moderate
        else:
            bar_colors.append("#76b7b2")   # teal = low
    ax_cost.barh(cost_df["Expense"], cost_df["Amount"], color=bar_colors)
    ax_cost.set_xlabel("Annual Amount ($)")
    ax_cost.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # Annotate % of revenue on each bar
    for i, (_, row) in enumerate(cost_df.iterrows()):
        ax_cost.text(
            row["Amount"] + y1_rev * 0.005, i,
            f"{row['% of Revenue']:.1%}",
            va="center", fontsize=8, color="#555",
        )

    ax_cost.set_title("Annual Expenses — Red = High Impact, Orange = Moderate, Teal = Low")
    plt.tight_layout()
    st.pyplot(fig_cost)
    plt.close(fig_cost)

    st.divider()

    # ---- Profitability calculations ----
    # F&B COGS
    fnb_rev = a["fnb"]["year1_revenue"]
    fnb_cogs = fnb_rev * a["fnb"]["cogs_pct"]
    gaming_rev = daily_hours * price * a["capacity"]["days_per_year"]
    total_rev_calc = gaming_rev + fnb_rev
    gross_profit = total_rev_calc - fnb_cogs

    orig_ebitda = gross_profit - original_opex
    adj_ebitda = gross_profit - adjusted_opex
    orig_ebit = orig_ebitda - depreciation
    adj_ebit = adj_ebitda - depreciation
    orig_pretax = orig_ebit - interest
    adj_pretax = adj_ebit - interest

    opex_savings = original_opex - adjusted_opex

    # ---- Impact Summary ----
    st.markdown("### Impact on Profitability")

    imp1, imp2, imp3, imp4 = st.columns(4)
    imp1.metric(
        "OpEx Savings",
        f"${opex_savings:,.0f}",
        delta=f"${opex_savings:+,.0f}" if opex_savings != 0 else None,
        delta_color="normal",
    )
    imp2.metric(
        "Adjusted EBITDA",
        f"${adj_ebitda:,.0f}",
        delta=f"${adj_ebitda - orig_ebitda:+,.0f}",
        delta_color="normal",
    )
    imp3.metric(
        "Adjusted Pre-Tax",
        f"${adj_pretax:,.0f}",
        delta=f"${adj_pretax - orig_pretax:+,.0f}",
        delta_color="normal",
    )
    # DSCR impact — DSCR = EBITDA / Total Debt Service
    annual_ds = a["debt"]["annual_principal_payment"] + interest
    adj_dscr = adj_ebitda / annual_ds if annual_ds > 0 else 0
    orig_dscr = orig_ebitda / annual_ds if annual_ds > 0 else 0
    imp4.metric(
        "Adjusted DSCR",
        f"{adj_dscr:.2f}x",
        delta=f"{adj_dscr - orig_dscr:+.2f}x",
        delta_color="normal",
    )

    # Side-by-side comparison table
    st.markdown("**Original vs Adjusted — Line-by-Line**")
    comparison_rows = []
    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            orig_val = y1_rev * a["fees"]["merchant_processing_pct"]
            adj_val = orig_val  # not adjustable
        elif name in adjustments_map:
            orig_val = base_amount
            adj_val = adjustments_map[name]
        else:
            orig_val = base_amount
            adj_val = base_amount

        delta = adj_val - orig_val
        comparison_rows.append({
            "Expense": name,
            "Original": f"${orig_val:,.0f}",
            "Adjusted": f"${adj_val:,.0f}",
            "Change ($)": f"${delta:+,.0f}" if delta != 0 else "—",
            "Adjustable": "Yes" if name in adjustments_map else "",
        })

    # Add payroll tax row
    comparison_rows.append({
        "Expense": "Payroll Taxes & Benefits",
        "Original": f"${payroll_tax_base:,.0f}",
        "Adjusted": f"${adj_payroll_tax:,.0f}",
        "Change ($)": f"${adj_payroll_tax - payroll_tax_base:+,.0f}" if adj_payroll_tax != payroll_tax_base else "—",
        "Adjustable": "(auto)",
    })

    comp_df = pd.DataFrame(comparison_rows)

    def highlight_changes(row):
        if row["Change ($)"] != "—":
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    styled_comp = comp_df.style.apply(highlight_changes, axis=1)
    st.dataframe(styled_comp, use_container_width=True, hide_index=True)

    # ---- Sensitivity: Which cost lever matters most? ----
    st.divider()
    st.markdown("### Cost Lever Sensitivity")
    st.caption(
        "Shows how a 10% cut to each major expense would improve EBITDA. "
        "Helps prioritize which negotiations or cuts have the most impact."
    )

    lever_impact = []
    for name, category, base_amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            continue  # variable cost, can't really negotiate
        savings_10pct = base_amount * 0.10
        lever_impact.append({
            "Expense": name,
            "Current": base_amount,
            "10% Cut": savings_10pct,
        })

    lever_df = pd.DataFrame(lever_impact).sort_values("10% Cut", ascending=True)

    fig_lever, ax_lever = plt.subplots(figsize=(8, 4.5))
    colors_lever = ["#59a14f" if v >= 3_000 else "#76b7b2" for v in lever_df["10% Cut"]]
    ax_lever.barh(lever_df["Expense"], lever_df["10% Cut"], color=colors_lever)
    ax_lever.set_xlabel("EBITDA Improvement from 10% Cut ($)")
    ax_lever.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_lever.set_title("Which Costs Move the Needle Most?")
    plt.tight_layout()
    st.pyplot(fig_lever)
    plt.close(fig_lever)

# --- TAB 10: Assumptions Lab ---
with tab10:
    import copy
    import config as config_module

    st.subheader("Assumptions Lab")
    st.caption(
        "Change any structural assumption and see how it flows through the full "
        "3-statement model. The base case (from config.py) is shown alongside "
        "your adjusted case so you can measure the impact of each change."
    )

    # ---- Current assumptions reference ----
    st.markdown("### Adjust Model Assumptions")

    alab_col1, alab_col2, alab_col3 = st.columns(3)

    with alab_col1:
        st.markdown("**Debt & Financing**")
        alab_loan = st.slider(
            "SBA Loan Amount ($)",
            min_value=100_000, max_value=300_000,
            value=a["debt"]["loan_amount"], step=10_000,
            help=f"Base: ${a['debt']['loan_amount']:,}. Total project cost = loan + equity.",
        )
        alab_rate = st.slider(
            "Interest Rate (%)",
            min_value=4.0, max_value=15.0,
            value=a["debt"]["interest_rate"] * 100, step=0.25,
            help=f"Base: {a['debt']['interest_rate']:.0%}. SBA 7(a) rates vary by market.",
        )
        alab_principal = st.slider(
            "Annual Principal Payment ($)",
            min_value=0, max_value=30_000,
            value=a["debt"]["annual_principal_payment"], step=1_000,
            help=f"Base: ${a['debt']['annual_principal_payment']:,}/yr.",
        )

    with alab_col2:
        st.markdown("**Growth & Revenue**")
        alab_rev_growth = st.slider(
            "Annual Revenue Growth (%)",
            min_value=0.0, max_value=10.0,
            value=a["growth"]["annual_revenue_growth"] * 100, step=0.5,
            help=f"Base: {a['growth']['annual_revenue_growth']:.1%}. Applied to Years 2+.",
        )
        alab_exp_growth = st.slider(
            "Annual Expense Growth (%)",
            min_value=0.0, max_value=10.0,
            value=a["growth"]["annual_expense_growth"] * 100, step=0.5,
            help=f"Base: {a['growth']['annual_expense_growth']:.1%}. Inflation/wage pressure.",
        )
        alab_fnb_rev = st.slider(
            "F&B / Merch Revenue ($/yr)",
            min_value=0, max_value=30_000,
            value=a["fnb"]["year1_revenue"], step=500,
            help=f"Base: ${a['fnb']['year1_revenue']:,}. Year 1 food, beverage, merch sales.",
        )

    with alab_col3:
        st.markdown("**COGS & Non-Cash**")
        alab_cogs = st.slider(
            "F&B COGS (%)",
            min_value=20.0, max_value=60.0,
            value=a["fnb"]["cogs_pct"] * 100, step=1.0,
            help=f"Base: {a['fnb']['cogs_pct']:.0%}. Cost of goods on food/beverage.",
        )
        alab_depreciation = st.slider(
            "Annual Depreciation ($)",
            min_value=10_000, max_value=40_000,
            value=a["depreciation"]["annual_depreciation"], step=1_000,
            help=f"Base: ${a['depreciation']['annual_depreciation']:,}. Non-cash charge for equipment wear.",
        )
        alab_merchant = st.slider(
            "Merchant Processing Fee (%)",
            min_value=1.0, max_value=5.0,
            value=a["fees"]["merchant_processing_pct"] * 100, step=0.25,
            help=f"Base: {a['fees']['merchant_processing_pct']:.0%}. Square/Stripe card fees.",
        )

    st.divider()

    # ---- Run adjusted model ----
    # Temporarily override config.ASSUMPTIONS, run the model, restore
    original_assumptions = copy.deepcopy(config_module.ASSUMPTIONS)

    try:
        config_module.ASSUMPTIONS["debt"]["loan_amount"] = alab_loan
        config_module.ASSUMPTIONS["debt"]["interest_rate"] = alab_rate / 100
        config_module.ASSUMPTIONS["debt"]["annual_principal_payment"] = alab_principal
        config_module.ASSUMPTIONS["debt"]["owner_equity"] = max(0, (alab_loan / 9))  # ~10% equity ratio
        config_module.ASSUMPTIONS["growth"]["annual_revenue_growth"] = alab_rev_growth / 100
        config_module.ASSUMPTIONS["growth"]["annual_expense_growth"] = alab_exp_growth / 100
        config_module.ASSUMPTIONS["fnb"]["year1_revenue"] = alab_fnb_rev
        config_module.ASSUMPTIONS["fnb"]["cogs_pct"] = alab_cogs / 100
        config_module.ASSUMPTIONS["depreciation"]["annual_depreciation"] = alab_depreciation
        config_module.ASSUMPTIONS["fees"]["merchant_processing_pct"] = alab_merchant / 100

        adj_model = build_full_model(
            daily_device_hours=daily_hours,
            price_per_hour=price,
            forecast_years=forecast_years,
        )
    finally:
        # Always restore original assumptions
        config_module.ASSUMPTIONS.update(copy.deepcopy(original_assumptions))

    adj_inc = adj_model["income_statement"]
    adj_cf = adj_model["cash_flow"]
    adj_ratios = adj_model["ratios"]

    # ---- Side-by-side KPI comparison ----
    st.markdown("### Impact: Base Case vs Adjusted")

    # Determine which years to show
    year_labels = [f"Year {i+1}" for i in range(forecast_years)]

    for yr_label in year_labels:
        st.markdown(f"**{yr_label}**")
        k1, k2, k3, k4, k5 = st.columns(5)

        base_rev = inc.loc["Total Revenue", yr_label]
        adj_rev_val = adj_inc.loc["Total Revenue", yr_label]
        k1.metric(
            "Total Revenue",
            f"${adj_rev_val:,.0f}",
            delta=f"${adj_rev_val - base_rev:+,.0f}" if abs(adj_rev_val - base_rev) > 0.5 else None,
            delta_color="normal",
        )

        base_ebitda = inc.loc["EBITDA", yr_label]
        adj_ebitda_val = adj_inc.loc["EBITDA", yr_label]
        k2.metric(
            "EBITDA",
            f"${adj_ebitda_val:,.0f}",
            delta=f"${adj_ebitda_val - base_ebitda:+,.0f}" if abs(adj_ebitda_val - base_ebitda) > 0.5 else None,
            delta_color="normal",
        )

        base_pretax = inc.loc["Pre-Tax Income", yr_label]
        adj_pretax_val = adj_inc.loc["Pre-Tax Income", yr_label]
        k3.metric(
            "Pre-Tax Income",
            f"${adj_pretax_val:,.0f}",
            delta=f"${adj_pretax_val - base_pretax:+,.0f}" if abs(adj_pretax_val - base_pretax) > 0.5 else None,
            delta_color="normal",
        )

        base_dscr = ratios.loc["DSCR", yr_label]
        adj_dscr_val = adj_ratios.loc["DSCR", yr_label]
        k4.metric(
            "DSCR",
            f"{adj_dscr_val:.2f}x",
            delta=f"{adj_dscr_val - base_dscr:+.2f}x" if abs(adj_dscr_val - base_dscr) > 0.005 else None,
            delta_color="normal",
        )

        base_cash = cf.loc["Ending Cash Balance", yr_label]
        adj_cash_val = adj_cf.loc["Ending Cash Balance", yr_label]
        k5.metric(
            "Ending Cash",
            f"${adj_cash_val:,.0f}",
            delta=f"${adj_cash_val - base_cash:+,.0f}" if abs(adj_cash_val - base_cash) > 0.5 else None,
            delta_color="normal",
        )

    st.divider()

    # ---- Adjusted Income Statement ----
    st.markdown("### Adjusted Income Statement")
    display_adj_inc = adj_inc.copy().astype(object)
    for col in display_adj_inc.columns:
        display_adj_inc[col] = display_adj_inc[col].apply(
            lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) and abs(x) > 1
            else f"{x:.1%}" if isinstance(x, float) and abs(x) <= 1
            else "" if pd.isna(x) else str(x)
        )
    st.dataframe(display_adj_inc, use_container_width=True, height=600)

    # ---- Assumptions delta table ----
    st.divider()
    st.markdown("### Assumptions Comparison")
    assumptions_compare = [
        {"Assumption": "SBA Loan Amount", "Base": f"${a['debt']['loan_amount']:,}", "Adjusted": f"${alab_loan:,}",
         "Change": f"${alab_loan - a['debt']['loan_amount']:+,}"},
        {"Assumption": "Interest Rate", "Base": f"{a['debt']['interest_rate']:.1%}", "Adjusted": f"{alab_rate/100:.1%}",
         "Change": f"{(alab_rate/100 - a['debt']['interest_rate'])*100:+.2f}pp"},
        {"Assumption": "Annual Principal Payment", "Base": f"${a['debt']['annual_principal_payment']:,}", "Adjusted": f"${alab_principal:,}",
         "Change": f"${alab_principal - a['debt']['annual_principal_payment']:+,}"},
        {"Assumption": "Revenue Growth", "Base": f"{a['growth']['annual_revenue_growth']:.1%}", "Adjusted": f"{alab_rev_growth/100:.1%}",
         "Change": f"{(alab_rev_growth/100 - a['growth']['annual_revenue_growth'])*100:+.2f}pp"},
        {"Assumption": "Expense Growth", "Base": f"{a['growth']['annual_expense_growth']:.1%}", "Adjusted": f"{alab_exp_growth/100:.1%}",
         "Change": f"{(alab_exp_growth/100 - a['growth']['annual_expense_growth'])*100:+.2f}pp"},
        {"Assumption": "F&B Revenue (Yr 1)", "Base": f"${a['fnb']['year1_revenue']:,}", "Adjusted": f"${alab_fnb_rev:,}",
         "Change": f"${alab_fnb_rev - a['fnb']['year1_revenue']:+,}"},
        {"Assumption": "F&B COGS %", "Base": f"{a['fnb']['cogs_pct']:.0%}", "Adjusted": f"{alab_cogs/100:.0%}",
         "Change": f"{(alab_cogs/100 - a['fnb']['cogs_pct'])*100:+.1f}pp"},
        {"Assumption": "Annual Depreciation", "Base": f"${a['depreciation']['annual_depreciation']:,}", "Adjusted": f"${alab_depreciation:,}",
         "Change": f"${alab_depreciation - a['depreciation']['annual_depreciation']:+,}"},
        {"Assumption": "Merchant Processing %", "Base": f"{a['fees']['merchant_processing_pct']:.0%}", "Adjusted": f"{alab_merchant/100:.0%}",
         "Change": f"{(alab_merchant/100 - a['fees']['merchant_processing_pct'])*100:+.1f}pp"},
    ]

    acomp_df = pd.DataFrame(assumptions_compare)

    def highlight_changed(row):
        # Check if anything actually changed
        if row["Base"] != row["Adjusted"]:
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    styled_acomp = acomp_df.style.apply(highlight_changed, axis=1)
    st.dataframe(styled_acomp, use_container_width=True, hide_index=True)

    # ---- Interest rate sensitivity chart ----
    st.divider()
    st.markdown("### Interest Rate Sensitivity")
    st.caption(
        "Shows how Pre-Tax Income changes across different interest rates, "
        "holding all other assumptions at their current slider values."
    )

    rate_range = [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
    rate_pretax = []

    for test_rate in rate_range:
        # Quick manual calculation for Year 1 only
        test_interest = alab_loan * (test_rate / 100)
        # Use adjusted model's EBIT (which doesn't depend on interest rate)
        test_ebit = adj_inc.loc["EBIT (Operating Income)", "Year 1"]
        test_pretax_val = test_ebit - test_interest
        rate_pretax.append(test_pretax_val)

    fig_rate, ax_rate = plt.subplots(figsize=(8, 4))
    bar_colors_rate = ["#59a14f" if v >= 0 else "#e15759" for v in rate_pretax]
    ax_rate.bar([f"{r:.0f}%" for r in rate_range], rate_pretax, color=bar_colors_rate, width=0.6)
    ax_rate.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax_rate.set_xlabel("Interest Rate")
    ax_rate.set_ylabel("Year 1 Pre-Tax Income ($)")
    ax_rate.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_rate.set_title("How Interest Rate Affects Year 1 Pre-Tax Income")

    # Mark current rate
    current_idx = None
    for i, r in enumerate(rate_range):
        if abs(r - alab_rate) < 0.01:
            current_idx = i
            break
    if current_idx is not None:
        ax_rate.get_children()[current_idx].set_edgecolor("black")
        ax_rate.get_children()[current_idx].set_linewidth(2)

    plt.tight_layout()
    st.pyplot(fig_rate)
    plt.close(fig_rate)

    # ---- Growth rate impact over forecast period ----
    st.markdown("### Revenue vs Expense Growth — Margin Trajectory")
    st.caption(
        "Shows how the spread between revenue growth and expense growth "
        "compounds over the forecast period. Margin expands when rev growth > exp growth."
    )

    margin_data = []
    for yr_label in year_labels:
        base_margin = inc.loc["EBITDA", yr_label] / inc.loc["Total Revenue", yr_label] if inc.loc["Total Revenue", yr_label] else 0
        adj_margin = adj_inc.loc["EBITDA", yr_label] / adj_inc.loc["Total Revenue", yr_label] if adj_inc.loc["Total Revenue", yr_label] else 0
        margin_data.append({
            "Year": yr_label,
            "Base EBITDA Margin": base_margin,
            "Adjusted EBITDA Margin": adj_margin,
        })

    margin_df = pd.DataFrame(margin_data)

    fig_margin, ax_margin = plt.subplots(figsize=(8, 4))
    x_pos = range(len(year_labels))
    width = 0.35
    ax_margin.bar([p - width/2 for p in x_pos], margin_df["Base EBITDA Margin"],
                  width=width, label="Base Case", color="#4e79a7", alpha=0.8)
    ax_margin.bar([p + width/2 for p in x_pos], margin_df["Adjusted EBITDA Margin"],
                  width=width, label="Adjusted", color="#59a14f", alpha=0.8)
    ax_margin.set_xticks(list(x_pos))
    ax_margin.set_xticklabels(year_labels)
    ax_margin.set_ylabel("EBITDA Margin")
    ax_margin.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax_margin.legend()
    ax_margin.set_title("EBITDA Margin: Base vs Adjusted Over Time")
    ax_margin.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    plt.tight_layout()
    st.pyplot(fig_margin)
    plt.close(fig_margin)

# --- TAB 11: Rolling Forecast ---
with tab11:
    st.subheader("Rolling Forecast & Latest Estimate")
    st.caption(
        f"Actuals through month {close_through} | "
        f"Reforecast method: {reforecast_method} | Scenario: {var_scenario}"
    )

    rf = build_rolling_forecast(
        daily_device_hours=daily_hours,
        price_per_hour=price,
        scenario=var_scenario,
        close_through_month=close_through,
        reforecast_method=reforecast_method,
    )

    # Latest Estimate summary
    le_summary = summarize_latest_estimate(rf)
    st.markdown("**Full-Year Latest Estimate**")

    le_cols = st.columns(4)
    for i, (metric, row) in enumerate(le_summary.iterrows()):
        with le_cols[i % 4]:
            var_pct = row["Variance (%)"]
            delta_str = f"{var_pct:+.1%}" if abs(var_pct) > 0.001 else None
            st.metric(
                metric,
                f"${row['Latest Estimate']:,.0f}",
                delta=delta_str,
                help=f"Budget: ${row['Full-Year Budget']:,.0f}",
            )

    st.divider()

    # Monthly rolling forecast chart — Revenue
    st.markdown("**Monthly Revenue: Actual vs Budget vs Forecast**")
    rev_rf = rf[rf["Metric"] == "Revenue"].copy()
    months_rf = rev_rf["Month"].tolist()

    fig_rf, ax_rf = plt.subplots(figsize=(10, 4))
    actual_mask = rev_rf["Source"] == "Actual"
    forecast_mask = rev_rf["Source"] == "Forecast"

    ax_rf.bar(
        [m for m, a in zip(months_rf, actual_mask) if a],
        rev_rf.loc[actual_mask, "Actual/Forecast"].tolist(),
        color="#4e79a7", label="Actual", width=0.4, align="edge",
    )
    ax_rf.bar(
        [m for m, f in zip(months_rf, forecast_mask) if f],
        rev_rf.loc[forecast_mask, "Actual/Forecast"].tolist(),
        color="#76b7b2", label="Forecast", width=0.4, align="edge",
    )
    ax_rf.plot(months_rf, rev_rf["Budget"].tolist(), linestyle="--", color="#888780",
               marker="o", markersize=4, label="Budget", linewidth=1.5)
    ax_rf.set_ylabel("Revenue ($)")
    ax_rf.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_rf.legend(fontsize=8)
    ax_rf.set_title("Rolling Forecast — Revenue")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig_rf)
    plt.close(fig_rf)

    # Forecast detail table
    st.divider()
    st.markdown("**Rolling Forecast Detail**")
    display_rf = rf.copy()
    display_rf["Budget"] = display_rf["Budget"].apply(lambda x: f"${x:,.0f}")
    display_rf["Actual/Forecast"] = display_rf["Actual/Forecast"].apply(lambda x: f"${x:,.0f}")
    display_rf["Variance ($)"] = display_rf["Variance ($)"].apply(lambda x: f"${x:+,.0f}")
    display_rf["Variance (%)"] = display_rf["Variance (%)"].apply(lambda x: f"{x:+.1%}")
    st.dataframe(display_rf, use_container_width=True, height=500)

    # Forecast accuracy
    st.divider()
    st.subheader("Forecast Accuracy Analysis")
    st.caption("How well did the budget predict actual results?")

    acc = compute_forecast_accuracy(
        daily_device_hours=daily_hours,
        price_per_hour=price,
        scenario=var_scenario,
    )
    acc_summary = summarize_forecast_accuracy(acc)

    acc_cols = st.columns(3)
    for i, (metric, row) in enumerate(acc_summary.iterrows()):
        with acc_cols[i % 3]:
            grade_colors = {
                "Excellent": "#d4edda", "Good": "#d4edda",
                "Needs Work": "#fff3cd", "Poor": "#f8d7da",
            }
            bg = grade_colors.get(row["Grade"], "#ffffff")
            st.markdown(
                f"<div style='background:{bg};padding:12px;border-radius:8px;margin-bottom:8px;'>"
                f"<div style='font-weight:700;'>{metric}</div>"
                f"<div>MAPE: {row['MAPE']:.1%} — <b>{row['Grade']}</b></div>"
                f"<div>Bias: ${row['Avg Bias ($)']:+,.0f} ({row['Bias Direction']})</div>"
                f"<div>Hit Rate (±5%): {row['Hit Rate (±5%)']:.0%}</div>"
                f"<div style='font-size:11px;color:#666;'>Worst: {row['Worst Month']} ({row['Worst Miss']:.1%})</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# --- TAB 12: Unit Economics ---
with tab12:
    st.subheader("Unit Economics & Driver-Based Metrics")
    st.caption(
        f"Per-unit economics at {daily_hours} daily device-hours, "
        f"${price:.2f}/hr, {calc_utilization(daily_hours):.1%} utilization"
    )

    metrics = compute_unit_economics(
        daily_device_hours=daily_hours,
        price_per_hour=price,
    )

    for group_name, group_metrics in metrics.items():
        st.markdown(f"### {group_name}")
        rows_ue = []
        for m in group_metrics:
            if m["Unit"] == "$":
                val_fmt = f"${m['Value']:,.2f}"
            elif m["Unit"] == "%":
                val_fmt = f"{m['Value']:.1%}"
            elif m["Unit"] == "months":
                if m["Value"] == float('inf'):
                    val_fmt = "N/A (negative EBITDA)"
                else:
                    val_fmt = f"{m['Value']:.1f} months"
            elif m["Unit"] == "hrs":
                val_fmt = f"{m['Value']:.0f} hrs"
            else:
                val_fmt = f"{m['Value']:.2f}"
            rows_ue.append({
                "Metric": m["Metric"],
                "Value": val_fmt,
                "Formula": m["Formula"],
                "Explanation": m["Explanation"],
            })
        st.dataframe(pd.DataFrame(rows_ue), use_container_width=True, hide_index=True)

    # Driver sensitivity
    st.divider()
    st.subheader("Driver Sensitivity — What Moves EBITDA Most?")
    st.caption("Each driver is tested at ±10% to show relative impact on EBITDA")

    driver_sens = build_driver_sensitivity(
        daily_device_hours=daily_hours,
        price_per_hour=price,
    )

    fig_drv, ax_drv = plt.subplots(figsize=(9, 4.5))
    colors_drv = ["#59a14f" if v >= 0 else "#e15759" for v in driver_sens["EBITDA Impact ($)"]]
    ax_drv.barh(driver_sens.index.tolist(), driver_sens["EBITDA Impact ($)"].tolist(), color=colors_drv)
    ax_drv.set_xlabel("EBITDA Impact ($)")
    ax_drv.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:+,.0f}"))
    ax_drv.axvline(x=0, color="gray", linewidth=0.8)
    ax_drv.set_title("EBITDA Impact of ±10% Change in Each Driver")
    plt.tight_layout()
    st.pyplot(fig_drv)
    plt.close(fig_drv)

    # Table
    display_drv = driver_sens.copy()
    display_drv["Base EBITDA"] = display_drv["Base EBITDA"].apply(lambda x: f"${x:,.0f}")
    display_drv["New EBITDA"] = display_drv["New EBITDA"].apply(lambda x: f"${x:,.0f}")
    display_drv["EBITDA Impact ($)"] = display_drv["EBITDA Impact ($)"].apply(lambda x: f"${x:+,.0f}")
    display_drv["EBITDA Impact (%)"] = display_drv["EBITDA Impact (%)"].apply(lambda x: f"{x:+.1%}")
    st.dataframe(display_drv, use_container_width=True)


# --- TAB 13: Executive Summary ---
with tab13:
    st.subheader("Executive Summary — Board-Ready Briefing")

    summary = generate_executive_summary(
        daily_device_hours=daily_hours,
        price_per_hour=price,
        forecast_years=forecast_years,
        scenario=var_scenario,
    )

    # Overall status badge
    status_colors = {"GREEN": "#d4edda", "AMBER": "#fff3cd", "RED": "#f8d7da"}
    status_text_colors = {"GREEN": "#155724", "AMBER": "#856404", "RED": "#721c24"}
    overall = summary["overall_status"]

    st.markdown(
        f"<div style='background:{status_colors[overall]};padding:16px;border-radius:8px;"
        f"border-left:6px solid {status_text_colors[overall]};margin-bottom:16px;'>"
        f"<div style='font-size:11px;font-weight:600;color:{status_text_colors[overall]};'>"
        f"OVERALL STATUS: {overall}</div>"
        f"<div style='font-size:16px;font-weight:700;color:{status_text_colors[overall]};'>"
        f"{summary['headline']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Key metrics row
    km = summary["key_metrics"]
    km_cols = st.columns(5)
    km_cols[0].metric("Total Revenue", f"${km['total_revenue']:,.0f}")
    km_cols[1].metric("EBITDA", f"${km['ebitda']:,.0f}")
    km_cols[2].metric("EBITDA Margin", f"{km['ebitda_margin']:.1%}")
    km_cols[3].metric("DSCR", f"{km['dscr']:.2f}x")
    km_cols[4].metric("Cash Runway", f"{km['cash_runway_months']:.1f} mo")

    st.divider()

    # Section cards
    st.markdown("### Performance Sections")
    for section in summary["sections"]:
        s = section["status"]
        st.markdown(
            f"<div style='background:{status_colors[s]};padding:14px;border-radius:8px;"
            f"border-left:4px solid {status_text_colors[s]};margin-bottom:10px;'>"
            f"<div style='font-weight:700;color:{status_text_colors[s]};'>"
            f"[{s}] {section['title']}</div>"
            f"<div style='color:#333;margin-top:4px;'>{section['narrative']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # Risks
    st.markdown("### Risk Register")
    if summary["risks"]:
        risk_rows = []
        for r in summary["risks"]:
            risk_rows.append({
                "Severity": r["severity"],
                "Risk": r["risk"],
                "Detail": r["detail"],
            })
        risk_df = pd.DataFrame(risk_rows)

        def color_severity(val):
            if val == "HIGH":
                return "background-color: #f8d7da; color: #721c24; font-weight: bold"
            elif val == "MEDIUM":
                return "background-color: #fff3cd; color: #856404; font-weight: bold"
            else:
                return "background-color: #d4edda; color: #155724"

        styled_risk = risk_df.style.map(color_severity, subset=["Severity"])
        st.dataframe(styled_risk, use_container_width=True, hide_index=True)
    else:
        st.success("No significant risks identified at current assumptions.")

    # Recommendations
    st.markdown("### Recommendations")
    for i, rec in enumerate(summary["recommendations"], 1):
        st.markdown(f"**{i}.** {rec}")

    # Metadata
    st.divider()
    st.caption(
        f"Scenario: {summary['metadata']['scenario']} | "
        f"Hours: {summary['metadata']['daily_hours']}/day | "
        f"Price: ${summary['metadata']['price_per_hour']:.2f}/hr | "
        f"Utilization: {summary['metadata']['utilization']:.1%} | "
        f"Forecast: {summary['metadata']['forecast_years']} years"
    )


# --- TAB 14: DCF Valuation ---
with tab14:
    st.subheader("DCF Business Valuation")
    st.caption(
        f"WACC: {dcf_wacc:.1f}% | Terminal Growth: {dcf_terminal_g:.1f}% | "
        f"Tax Rate: {dcf_tax_rate:.0f}% | Forecast: 5 years"
    )

    dcf = build_dcf_valuation(
        daily_device_hours=daily_hours,
        price_per_hour=price,
        forecast_years=5,
        wacc=dcf_wacc / 100,
        terminal_growth_rate=dcf_terminal_g / 100,
        tax_rate=dcf_tax_rate / 100,
    )

    # Valuation summary
    st.markdown("### Valuation Summary")
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Enterprise Value", f"${dcf['enterprise_value']:,.0f}")
    v2.metric("Equity Value", f"${dcf['equity_value']:,.0f}")
    v3.metric("EV / EBITDA", f"{dcf['metrics']['ev_to_ebitda']:.1f}x")
    v4.metric("ROI on Equity", f"{dcf['metrics']['roi_on_equity']:.1%}")

    v5, v6, v7, v8 = st.columns(4)
    v5.metric("PV of UFCFs", f"${dcf['pv_ufcf_total']:,.0f}")
    v6.metric("PV of Terminal Value", f"${dcf['pv_terminal']:,.0f}")
    v7.metric("TV as % of EV", f"{dcf['metrics']['tv_as_pct_of_ev']:.1%}")
    v8.metric("ROI on Total Investment", f"{dcf['metrics']['roi_on_total_investment']:.1%}")

    st.divider()

    # Enterprise-to-Equity bridge chart
    st.markdown("### Enterprise-to-Equity Value Bridge")
    bridge_labels = ["PV of UFCFs", "PV of Terminal Value", "Enterprise Value", "Less: Net Debt", "Equity Value"]
    bridge_values = [
        dcf['pv_ufcf_total'],
        dcf['pv_terminal'],
        dcf['enterprise_value'],
        -dcf['net_debt'],
        dcf['equity_value'],
    ]
    bridge_colors = ["#4e79a7", "#4e79a7", "#59a14f", "#e15759", "#59a14f"]

    fig_bridge, ax_bridge = plt.subplots(figsize=(9, 4))
    ax_bridge.bar(bridge_labels, bridge_values, color=bridge_colors, width=0.5)
    ax_bridge.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_bridge.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
    ax_bridge.set_title("DCF Valuation: Enterprise to Equity Bridge")
    plt.xticks(rotation=15, fontsize=9)
    plt.tight_layout()
    st.pyplot(fig_bridge)
    plt.close(fig_bridge)

    # UFCF schedule
    st.divider()
    st.markdown("### Unlevered Free Cash Flow Schedule")
    ufcf_df = dcf["ufcf_schedule"]
    display_ufcf = ufcf_df.copy().astype(object)
    for idx in display_ufcf.index:
        for col in display_ufcf.columns:
            val = display_ufcf.loc[idx, col]
            if not isinstance(val, (int, float)):
                display_ufcf.loc[idx, col] = ""
            elif "Tax Rate" in idx:
                display_ufcf.loc[idx, col] = f"{val:.0%}"
            else:
                display_ufcf.loc[idx, col] = f"${val:,.0f}"
    st.dataframe(display_ufcf, use_container_width=True)

    # Discount factor detail
    st.markdown("### Present Value Detail")
    pv_rows = []
    for i in range(len(dcf["ufcf_values"])):
        pv_rows.append({
            "Year": f"Year {i+1}",
            "UFCF": f"${dcf['ufcf_values'][i]:,.0f}",
            "Discount Factor": f"{1/dcf['discount_factors'][i]:.4f}",
            "PV of UFCF": f"${dcf['pv_ufcfs'][i]:,.0f}",
        })
    pv_rows.append({
        "Year": "Terminal",
        "UFCF": f"${dcf['terminal_ufcf']:,.0f}",
        "Discount Factor": f"{1/dcf['discount_factors'][-1]:.4f}",
        "PV of UFCF": f"${dcf['pv_terminal']:,.0f}",
    })
    st.dataframe(pd.DataFrame(pv_rows), use_container_width=True, hide_index=True)

    # DCF sensitivity table
    st.divider()
    st.markdown("### Sensitivity: Equity Value (WACC vs Terminal Growth)")
    st.caption("How sensitive is the valuation to changes in WACC and terminal growth rate?")

    dcf_sens = build_dcf_sensitivity(
        daily_device_hours=daily_hours,
        price_per_hour=price,
        forecast_years=5,
        tax_rate=dcf_tax_rate / 100,
    )

    def color_equity(val):
        if isinstance(val, (int, float)):
            if val == float('inf'):
                return ""
            if val > 0:
                return "background-color: #d4edda"
            else:
                return "background-color: #f8d7da"
        return ""

    def fmt_equity(val):
        if isinstance(val, (int, float)):
            if val == float('inf'):
                return "N/A"
            return f"${val:,.0f}"
        return str(val)

    styled_dcf_sens = dcf_sens.style.map(color_equity).format(fmt_equity)
    st.dataframe(styled_dcf_sens, use_container_width=True)

    # Assumptions
    st.divider()
    st.caption(
        f"Assumptions: WACC {dcf_wacc:.1f}% | Terminal Growth {dcf_terminal_g:.1f}% | "
        f"Tax Rate {dcf_tax_rate:.0f}% | CapEx 2% of Rev | NWC 5% of Rev | "
        f"Total Investment: ${dcf['metrics']['total_investment']:,} | "
        f"Owner Equity: ${dcf['metrics']['owner_equity']:,}"
    )


# --- TAB 15: Time-Block Revenue ---
with tab15:
    st.subheader("Time-Block Revenue Model")
    st.caption(
        "Break the operating day into time blocks with different utilization "
        "and pricing. Compare flat-rate vs time-block revenue."
    )

    # Time-block definitions
    st.markdown("### Configure Time Blocks")
    st.caption("Set utilization and price for each time segment (10 AM – 10 PM)")

    tb_col1, tb_col2, tb_col3, tb_col4 = st.columns(4)

    with tb_col1:
        st.markdown("**Morning (10AM–1PM)**")
        tb_morning_util = st.slider("Morning Util %", 5, 60, 12, 1, key="tb_m_u") / 100
        tb_morning_price = st.slider("Morning $/hr", 5.0, 15.0, 7.00, 0.50, key="tb_m_p")

    with tb_col2:
        st.markdown("**Afternoon (1PM–5PM)**")
        tb_afternoon_util = st.slider("Afternoon Util %", 5, 60, 18, 1, key="tb_a_u") / 100
        tb_afternoon_price = st.slider("Afternoon $/hr", 5.0, 15.0, 9.00, 0.50, key="tb_a_p")

    with tb_col3:
        st.markdown("**Peak (5PM–9PM)**")
        tb_peak_util = st.slider("Peak Util %", 5, 80, 35, 1, key="tb_pk_u") / 100
        tb_peak_price = st.slider("Peak $/hr", 5.0, 18.0, 11.00, 0.50, key="tb_pk_p")

    with tb_col4:
        st.markdown("**Late Night (9PM–10PM)**")
        tb_late_util = st.slider("Late Util %", 5, 60, 15, 1, key="tb_l_u") / 100
        tb_late_price = st.slider("Late $/hr", 5.0, 15.0, 8.00, 0.50, key="tb_l_p")

    st.divider()

    # Calculate time-block revenue
    stations = a["capacity"]["total_devices"]
    days_yr = a["capacity"]["days_per_year"]

    time_blocks = [
        {"Block": "Morning (10AM–1PM)", "Hours": 3, "Utilization": tb_morning_util, "Price": tb_morning_price},
        {"Block": "Afternoon (1PM–5PM)", "Hours": 4, "Utilization": tb_afternoon_util, "Price": tb_afternoon_price},
        {"Block": "Peak (5PM–9PM)", "Hours": 4, "Utilization": tb_peak_util, "Price": tb_peak_price},
        {"Block": "Late Night (9PM–10PM)", "Hours": 1, "Utilization": tb_late_util, "Price": tb_late_price},
    ]

    tb_rows = []
    total_tb_daily_rev = 0
    total_tb_daily_hours = 0
    for block in time_blocks:
        max_station_hrs = stations * block["Hours"]
        sold_hrs = max_station_hrs * block["Utilization"]
        daily_rev = sold_hrs * block["Price"]
        total_tb_daily_rev += daily_rev
        total_tb_daily_hours += sold_hrs
        tb_rows.append({
            "Time Block": block["Block"],
            "Duration (hrs)": block["Hours"],
            "Max Station-Hrs": max_station_hrs,
            "Utilization": f"{block['Utilization']:.0%}",
            "Hours Sold": f"{sold_hrs:.0f}",
            "Price/Hr": f"${block['Price']:.2f}",
            "Daily Revenue": f"${daily_rev:,.0f}",
        })

    tb_rows.append({
        "Time Block": "TOTAL",
        "Duration (hrs)": 12,
        "Max Station-Hrs": stations * 12,
        "Utilization": f"{total_tb_daily_hours / (stations * 12):.1%}",
        "Hours Sold": f"{total_tb_daily_hours:.0f}",
        "Price/Hr": f"${total_tb_daily_rev / total_tb_daily_hours:.2f}" if total_tb_daily_hours > 0 else "$0",
        "Daily Revenue": f"${total_tb_daily_rev:,.0f}",
    })

    st.markdown("### Time-Block Revenue Breakdown")
    st.dataframe(pd.DataFrame(tb_rows), use_container_width=True, hide_index=True)

    # Comparison: flat vs time-block
    st.divider()
    st.markdown("### Flat-Rate vs Time-Block Comparison")

    flat_daily_rev = daily_hours * price
    flat_annual = flat_daily_rev * days_yr
    tb_annual = total_tb_daily_rev * days_yr
    revenue_delta = tb_annual - flat_annual

    comp1, comp2, comp3, comp4 = st.columns(4)
    comp1.metric("Flat-Rate Annual", f"${flat_annual:,.0f}",
                 help=f"{daily_hours} hrs × ${price:.2f} × 365")
    comp2.metric("Time-Block Annual", f"${tb_annual:,.0f}",
                 help="Sum of all block revenues × 365")
    comp3.metric("Revenue Uplift", f"${revenue_delta:+,.0f}",
                 delta=f"{revenue_delta/flat_annual:+.1%}" if flat_annual else None)
    comp4.metric("Blended Rate", f"${total_tb_daily_rev/total_tb_daily_hours:.2f}/hr" if total_tb_daily_hours > 0 else "N/A",
                 help="Effective average price per hour across all blocks")

    # Visual: revenue by block
    st.markdown("### Revenue by Time Block")
    block_names = [b["Block"] for b in time_blocks]
    block_revs = [b["Utilization"] * stations * b["Hours"] * b["Price"] * days_yr for b in time_blocks]
    block_colors = ["#76b7b2", "#4e79a7", "#59a14f", "#f28e2b"]

    fig_tb, ax_tb = plt.subplots(figsize=(8, 4))
    bars = ax_tb.bar(block_names, block_revs, color=block_colors, width=0.5)
    ax_tb.axhline(y=flat_annual / 4, color="red", linewidth=1, linestyle="--",
                  label=f"Flat avg per block: ${flat_annual/4:,.0f}")
    ax_tb.set_ylabel("Annual Revenue ($)")
    ax_tb.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_tb.set_title("Annual Gaming Revenue by Time Block")
    ax_tb.legend(fontsize=8)
    for bar, rev in zip(bars, block_revs):
        ax_tb.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                   f"${rev:,.0f}", ha="center", va="bottom", fontsize=8)
    plt.xticks(fontsize=9)
    plt.tight_layout()
    st.pyplot(fig_tb)
    plt.close(fig_tb)

    # Utilization heatmap
    st.markdown("### Daily Utilization Profile")
    util_data = {b["Block"]: [b["Utilization"]] for b in time_blocks}
    util_df = pd.DataFrame(util_data, index=["Utilization"])

    fig_util, ax_util = plt.subplots(figsize=(8, 1.5))
    util_vals = [b["Utilization"] for b in time_blocks]
    bar_colors_util = []
    for u in util_vals:
        if u >= 0.30:
            bar_colors_util.append("#59a14f")
        elif u >= 0.20:
            bar_colors_util.append("#f28e2b")
        else:
            bar_colors_util.append("#e15759")
    ax_util.barh(["Utilization"], [time_blocks[0]["Hours"]], left=0, color=bar_colors_util[0], label=f"Morning: {util_vals[0]:.0%}")
    left = time_blocks[0]["Hours"]
    for i in range(1, len(time_blocks)):
        ax_util.barh(["Utilization"], [time_blocks[i]["Hours"]], left=left,
                     color=bar_colors_util[i], label=f"{time_blocks[i]['Block'].split('(')[0].strip()}: {util_vals[i]:.0%}")
        left += time_blocks[i]["Hours"]
    ax_util.set_xlabel("Hours of Day")
    ax_util.set_title("Operating Day — Color = Utilization (Green > 30%, Orange > 20%, Red < 20%)")
    ax_util.legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    plt.tight_layout()
    st.pyplot(fig_util)
    plt.close(fig_util)


# --- TAB 16: Financial Metrics Reference ---
with tab16:
    st.subheader("Financial Metrics Reference")
    st.caption("Searchable reference of key financial metrics used in this model")

    # Metrics database
    METRICS_DB = [
        {"Category": "Profitability", "Metric": "Gross Margin", "Formula": "Gross Profit ÷ Revenue",
         "Meaning": "% of revenue retained after direct costs (COGS). For service businesses like gaming arenas, expect 95%+.",
         "Good Range": "> 50%", "Used In": "Income Statement, KPI Scorecard"},
        {"Category": "Profitability", "Metric": "EBITDA Margin", "Formula": "EBITDA ÷ Revenue",
         "Meaning": "Operating profitability before non-cash charges and financing. Shows core business earning power.",
         "Good Range": "> 15%", "Used In": "Income Statement, Executive Summary"},
        {"Category": "Profitability", "Metric": "Pre-Tax Margin", "Formula": "Pre-Tax Income ÷ Revenue",
         "Meaning": "Bottom-line profitability before taxes. Captures full P&L including debt service impact.",
         "Good Range": "> 5%", "Used In": "Income Statement, Scenarios"},
        {"Category": "Profitability", "Metric": "Return on Assets (ROA)", "Formula": "Pre-Tax Income ÷ Total Assets",
         "Meaning": "How efficiently assets generate income. Measures capital deployment effectiveness.",
         "Good Range": "> 5%", "Used In": "Ratios"},
        {"Category": "Profitability", "Metric": "Return on Equity (ROE)", "Formula": "Pre-Tax Income ÷ Owner Equity",
         "Meaning": "Return generated for the owner. High leverage amplifies this (both up and down).",
         "Good Range": "> 15%", "Used In": "Ratios"},
        {"Category": "Leverage", "Metric": "DSCR (Debt Service Coverage)", "Formula": "EBITDA ÷ (Interest + Principal)",
         "Meaning": "Can the business pay its debt? SBA minimum is 1.25x. Below 1.0x means cash shortfall.",
         "Good Range": "> 1.25x", "Used In": "Ratios, KPI Scorecard, Breakeven, Monte Carlo"},
        {"Category": "Leverage", "Metric": "Debt-to-Equity", "Formula": "Total Liabilities ÷ Total Equity",
         "Meaning": "Financial leverage. Higher = more debt-financed. SBA-funded startups are typically high.",
         "Good Range": "< 3.0x", "Used In": "Ratios, Balance Sheet"},
        {"Category": "Liquidity", "Metric": "Cash Runway", "Formula": "Cash Balance ÷ Monthly OpEx",
         "Meaning": "Months of operations cash can sustain without revenue. Safety buffer measure.",
         "Good Range": "> 3 months", "Used In": "Ratios, Executive Summary"},
        {"Category": "Operations", "Metric": "Utilization Rate", "Formula": "Daily Hours Sold ÷ Max Daily Hours",
         "Meaning": "THE #1 KPI. % of available capacity being used. Drives revenue and unit economics.",
         "Good Range": "> 20%", "Used In": "Unit Economics, Scenarios, Breakeven"},
        {"Category": "Operations", "Metric": "Revenue per Station per Day", "Formula": "Total Revenue ÷ (Stations × 365)",
         "Meaning": "Daily productivity of each gaming station. Key operational efficiency metric.",
         "Good Range": "> $20", "Used In": "Unit Economics"},
        {"Category": "Operations", "Metric": "Contribution Margin per Hour", "Formula": "(Gaming Rev - Variable Costs) ÷ Hours Sold",
         "Meaning": "Incremental profit from selling one more hour. Pricing floor for promotions.",
         "Good Range": "> $5", "Used In": "Unit Economics"},
        {"Category": "Valuation", "Metric": "EV / EBITDA", "Formula": "Enterprise Value ÷ EBITDA",
         "Meaning": "How many years of EBITDA the business is 'worth.' Lower = cheaper valuation.",
         "Good Range": "4-8x", "Used In": "DCF Valuation"},
        {"Category": "Valuation", "Metric": "WACC", "Formula": "Weighted avg of cost of equity and cost of debt",
         "Meaning": "Discount rate for DCF. Represents the minimum return investors require.",
         "Good Range": "8-15%", "Used In": "DCF Valuation"},
        {"Category": "Valuation", "Metric": "Terminal Value", "Formula": "UFCF × (1+g) ÷ (WACC - g)",
         "Meaning": "Value of all cash flows beyond the explicit forecast period. Often 60-80% of total EV.",
         "Good Range": "< 75% of EV", "Used In": "DCF Valuation"},
        {"Category": "Valuation", "Metric": "Unlevered Free Cash Flow (UFCF)", "Formula": "NOPAT + D&A - CapEx - ΔNWC",
         "Meaning": "Cash flow available to all capital providers (debt + equity). The DCF input.",
         "Good Range": "Positive", "Used In": "DCF Valuation"},
        {"Category": "Variance", "Metric": "MAPE", "Formula": "Mean of |Actual - Budget| ÷ |Budget|",
         "Meaning": "Average forecast error. Lower = better forecasting. <5% is excellent.",
         "Good Range": "< 10%", "Used In": "Rolling Forecast"},
        {"Category": "Variance", "Metric": "Forecast Bias", "Formula": "Mean of (Actual - Budget)",
         "Meaning": "Systematic over/under-forecasting. Positive = conservative budget.",
         "Good Range": "Near $0", "Used In": "Rolling Forecast"},
        {"Category": "Cost", "Metric": "Operating Leverage", "Formula": "Fixed Costs ÷ Total Costs",
         "Meaning": "How much of cost base is fixed. Higher = more upside from revenue growth, more downside risk.",
         "Good Range": "Context-dependent", "Used In": "Unit Economics"},
        {"Category": "Cost", "Metric": "Occupancy Cost Ratio", "Formula": "Rent ÷ Revenue",
         "Meaning": "Rent burden relative to revenue. Retail rule of thumb: <25% for viability.",
         "Good Range": "< 25%", "Used In": "Executive Summary, Cost Drivers"},
        {"Category": "Payback", "Metric": "Equipment Payback Period", "Formula": "Total Startup Cost ÷ Annual EBITDA × 12",
         "Meaning": "Months until cumulative EBITDA covers initial investment. Shorter = better.",
         "Good Range": "< 36 months", "Used In": "Unit Economics"},
    ]

    # Search filter
    search_term = st.text_input("Search metrics", "", placeholder="Type to filter (e.g., DSCR, margin, cash)...")
    category_filter = st.multiselect(
        "Filter by category",
        options=sorted(set(m["Category"] for m in METRICS_DB)),
        default=[],
    )

    # Apply filters
    filtered = METRICS_DB
    if search_term:
        search_lower = search_term.lower()
        filtered = [m for m in filtered
                    if search_lower in m["Metric"].lower()
                    or search_lower in m["Meaning"].lower()
                    or search_lower in m["Formula"].lower()]
    if category_filter:
        filtered = [m for m in filtered if m["Category"] in category_filter]

    st.caption(f"Showing {len(filtered)} of {len(METRICS_DB)} metrics")

    # Display as cards
    for m in filtered:
        cat_colors = {
            "Profitability": "#4e79a7", "Leverage": "#e15759", "Liquidity": "#76b7b2",
            "Operations": "#59a14f", "Valuation": "#f28e2b", "Variance": "#edc948",
            "Cost": "#b07aa1", "Payback": "#ff9da7",
        }
        color = cat_colors.get(m["Category"], "#888")
        st.markdown(
            f"<div style='border-left:4px solid {color};padding:12px;margin-bottom:10px;"
            f"background:#f8f9fa;border-radius:4px;'>"
            f"<div style='font-weight:700;font-size:15px;'>{m['Metric']}"
            f"<span style='font-size:11px;color:{color};margin-left:8px;'>[{m['Category']}]</span></div>"
            f"<div style='font-family:monospace;color:#555;margin:4px 0;'>{m['Formula']}</div>"
            f"<div style='color:#333;'>{m['Meaning']}</div>"
            f"<div style='font-size:12px;color:#666;margin-top:4px;'>"
            f"Target: <b>{m['Good Range']}</b> | Used in: {m['Used In']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# --- TAB 17: Model Integrity ---
with tab17:
    st.subheader("Model Integrity Checks")
    st.caption(
        "Automated validation of balance sheet balances, cross-statement consistency, "
        "DSCR recalculation, and reasonableness checks."
    )

    integrity_checks = run_integrity_checks(
        daily_device_hours=daily_hours,
        price_per_hour=price,
        forecast_years=forecast_years,
    )
    integrity_summary = summarize_integrity(integrity_checks)

    # Overall scorecard
    overall_status = integrity_summary["overall"]
    if "FAIL" in overall_status:
        overall_bg = "#f8d7da"
        overall_tc = "#721c24"
    elif "warning" in overall_status.lower():
        overall_bg = "#fff3cd"
        overall_tc = "#856404"
    else:
        overall_bg = "#d4edda"
        overall_tc = "#155724"

    st.markdown(
        f"<div style='background:{overall_bg};padding:16px;border-radius:8px;"
        f"border-left:6px solid {overall_tc};margin-bottom:16px;'>"
        f"<div style='font-size:24px;font-weight:700;color:{overall_tc};'>{overall_status}</div>"
        f"<div style='font-size:14px;color:{overall_tc};'>"
        f"{integrity_summary['passed']} passed | "
        f"{integrity_summary['failed']} failed | "
        f"{integrity_summary['warnings']} warnings | "
        f"Pass rate: {integrity_summary['pass_rate']:.0%}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Summary metrics
    ic1, ic2, ic3, ic4 = st.columns(4)
    ic1.metric("Total Checks", f"{integrity_summary['total_checks']}")
    ic2.metric("Passed", f"{integrity_summary['passed']}", delta_color="normal")
    ic3.metric("Failed", f"{integrity_summary['failed']}",
               delta=f"{integrity_summary['failed']}" if integrity_summary['failed'] > 0 else None,
               delta_color="inverse")
    ic4.metric("Critical Failures", f"{integrity_summary['critical_failures']}",
               delta=f"{integrity_summary['critical_failures']}" if integrity_summary['critical_failures'] > 0 else None,
               delta_color="inverse")

    st.divider()

    # Detailed check results by category
    st.markdown("### Check Results by Category")

    categories = sorted(set(c["Category"] for c in integrity_checks))
    for cat in categories:
        cat_checks = [c for c in integrity_checks if c["Category"] == cat]
        cat_passed = sum(1 for c in cat_checks if c["Status"] == "PASS")
        cat_total = len(cat_checks)

        with st.expander(f"{cat} — {cat_passed}/{cat_total} passed", expanded=(cat_passed < cat_total)):
            for c in cat_checks:
                if c["Status"] == "PASS":
                    icon = "✅"
                    bg = "#d4edda"
                elif c["Status"] == "FAIL":
                    icon = "❌"
                    bg = "#f8d7da"
                else:
                    icon = "⚠️"
                    bg = "#fff3cd"

                st.markdown(
                    f"<div style='background:{bg};padding:8px 12px;border-radius:4px;margin-bottom:4px;'>"
                    f"{icon} <b>{c['Check']}</b> "
                    f"<span style='font-size:11px;color:#666;'>[{c['Severity']}]</span><br>"
                    f"<span style='font-size:12px;color:#555;'>{c['Detail']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # Full results table
    st.divider()
    st.markdown("### Full Results Table")
    check_df = pd.DataFrame(integrity_checks)

    def color_check_status(val):
        if val == "PASS":
            return "background-color: #d4edda; color: #155724; font-weight: bold"
        elif val == "FAIL":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold"
        elif val == "WARNING":
            return "background-color: #fff3cd; color: #856404; font-weight: bold"
        return ""

    def color_severity(val):
        if val == "CRITICAL":
            return "color: #721c24; font-weight: bold"
        elif val == "HIGH":
            return "color: #856404; font-weight: bold"
        return ""

    styled_checks = check_df.style.map(color_check_status, subset=["Status"]).map(
        color_severity, subset=["Severity"]
    )
    st.dataframe(styled_checks, use_container_width=True, hide_index=True)


# --- TAB 18: Accounting & GL ---
with tab18:
    st.subheader("Accounting & General Ledger")
    st.caption(
        "GAAP double-entry accounting flow: Journal Entries → General Ledger → "
        "Trial Balance → Financial Statements. All transactions for Year 1 (monthly)."
    )

    # ---- Sub-section selector ----
    acct_section = st.radio(
        "Section",
        ["Chart of Accounts", "Journal Entries", "General Ledger",
         "Trial Balance", "GL → Financial Statements"],
        horizontal=True,
    )

    st.divider()

    # ---- CHART OF ACCOUNTS ----
    if acct_section == "Chart of Accounts":
        st.markdown("### Chart of Accounts (GAAP Structure)")
        st.caption(
            "Standard GAAP numbering: 1xxx = Assets, 2xxx = Liabilities, "
            "3xxx = Equity, 4xxx = Revenue, 5xxx = COGS, 6xxx = OpEx, 7xxx = Other. "
            "Normal balance shows the side that increases the account."
        )

        coa_df = get_chart_of_accounts_df()

        # Color by type
        type_colors = {
            "Asset": "#4e79a7", "Liability": "#e15759", "Equity": "#59a14f",
            "Revenue": "#76b7b2", "Expense": "#f28e2b",
        }

        def color_acct_type(val):
            color = type_colors.get(val, "#888")
            return f"color: {color}; font-weight: bold"

        styled_coa = coa_df.style.map(color_acct_type, subset=["Type"])
        st.dataframe(styled_coa, use_container_width=True, hide_index=True, height=700)

        # Visual: account distribution
        st.markdown("### Account Distribution by Type")
        type_counts = coa_df["Type"].value_counts()
        fig_coa, ax_coa = plt.subplots(figsize=(6, 3))
        bars_coa = ax_coa.barh(
            type_counts.index.tolist(),
            type_counts.values.tolist(),
            color=[type_colors.get(t, "#888") for t in type_counts.index],
        )
        ax_coa.set_xlabel("Number of Accounts")
        ax_coa.set_title("Chart of Accounts by Type")
        for bar, count in zip(bars_coa, type_counts.values):
            ax_coa.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                       str(count), va="center", fontsize=10)
        plt.tight_layout()
        st.pyplot(fig_coa)
        plt.close(fig_coa)

    # ---- JOURNAL ENTRIES ----
    elif acct_section == "Journal Entries":
        st.markdown("### Journal Entries — Year 1 (Monthly)")
        st.caption(
            "Every business transaction is recorded as a journal entry with equal "
            "debits and credits. This is the foundation of double-entry bookkeeping."
        )

        je_df = get_journal_entries_df(daily_device_hours=daily_hours, price_per_hour=price)
        n_entries = je_df["JE #"].nunique()
        total_dr = je_df["Debit"].sum()
        total_cr = je_df["Credit"].sum()

        # Summary metrics
        je_m1, je_m2, je_m3, je_m4 = st.columns(4)
        je_m1.metric("Total Entries", f"{n_entries}")
        je_m2.metric("Total Lines", f"{len(je_df)}")
        je_m3.metric("Total Debits", f"${total_dr:,.0f}")
        je_m4.metric("Total Credits", f"${total_cr:,.0f}")

        st.divider()

        # Filter controls
        je_filter_col1, je_filter_col2 = st.columns(2)
        with je_filter_col1:
            month_filter = st.selectbox(
                "Filter by Month",
                ["All"] + sorted(je_df["Date"].unique().tolist(),
                                key=lambda x: int(x.split()[-1]) if x != "Month 0" else -1),
            )
        with je_filter_col2:
            ref_filter = st.selectbox(
                "Filter by Type",
                ["All"] + sorted(je_df["Reference"].unique().tolist()),
            )

        display_je = je_df.copy()
        if month_filter != "All":
            display_je = display_je[display_je["Date"] == month_filter]
        if ref_filter != "All":
            display_je = display_je[display_je["Reference"] == ref_filter]

        # Format for display
        display_je_fmt = display_je.copy()
        display_je_fmt["Debit"] = display_je_fmt["Debit"].apply(
            lambda x: f"${x:,.2f}" if x > 0 else "")
        display_je_fmt["Credit"] = display_je_fmt["Credit"].apply(
            lambda x: f"${x:,.2f}" if x > 0 else "")

        st.dataframe(display_je_fmt, use_container_width=True, hide_index=True, height=600)

        # JE type breakdown
        st.divider()
        st.markdown("### Entry Breakdown by Type")
        je_by_ref = je_df.groupby("Reference").agg(
            Entries=("JE #", "nunique"),
            Total_Debits=("Debit", "sum"),
        ).sort_values("Total_Debits", ascending=False)

        fig_je, ax_je = plt.subplots(figsize=(8, 3.5))
        ref_colors = {"Opening": "#4e79a7", "Revenue": "#59a14f", "COGS": "#e15759",
                      "OpEx": "#f28e2b", "Non-Cash": "#76b7b2", "Financing": "#b07aa1"}
        colors_je = [ref_colors.get(r, "#888") for r in je_by_ref.index]
        ax_je.barh(je_by_ref.index.tolist(), je_by_ref["Total_Debits"].tolist(), color=colors_je)
        ax_je.set_xlabel("Total Debits ($)")
        ax_je.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax_je.set_title("Journal Entries by Category — Total Activity")
        plt.tight_layout()
        st.pyplot(fig_je)
        plt.close(fig_je)

    # ---- GENERAL LEDGER ----
    elif acct_section == "General Ledger":
        st.markdown("### General Ledger — Monthly Running Balances")
        st.caption(
            "The GL is the master accounting record. Every journal entry is posted here, "
            "organized by account with running balances. Select an account to see its full ledger."
        )

        gl_df = build_general_ledger(daily_device_hours=daily_hours, price_per_hour=price)

        # Account selector
        acct_options = []
        for acct_num, info in CHART_OF_ACCOUNTS.items():
            acct_gl = gl_df[gl_df["Account #"] == acct_num]
            if not acct_gl.empty:
                ending = acct_gl.iloc[-1]["Balance"]
                acct_options.append(f"{acct_num} — {info['name']} (Bal: ${ending:,.0f})")

        selected_acct_str = st.selectbox("Select Account", acct_options)
        selected_acct = selected_acct_str.split(" — ")[0] if selected_acct_str else "1000"

        acct_info = CHART_OF_ACCOUNTS[selected_acct]
        st.markdown(
            f"**{acct_info['name']}** | Type: {acct_info['type'].title()} | "
            f"Normal Balance: {acct_info['normal_balance'].title()} | "
            f"Maps to: {acct_info['fs']} → {acct_info['fs_line']}"
        )

        acct_ledger = gl_df[gl_df["Account #"] == selected_acct].copy()

        # Format for display
        display_gl = acct_ledger[["Date", "JE #", "Description", "Debit", "Credit", "Balance"]].copy()
        display_gl["Debit"] = display_gl["Debit"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) and x > 0 else "")
        display_gl["Credit"] = display_gl["Credit"].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) and x > 0 else "")
        display_gl["Balance"] = display_gl["Balance"].apply(lambda x: f"${x:,.2f}")

        st.dataframe(display_gl, use_container_width=True, hide_index=True, height=500)

        # Balance trend chart
        if not acct_ledger.empty and len(acct_ledger) > 1:
            st.markdown(f"### {acct_info['name']} — Balance Over Time")
            fig_gl, ax_gl = plt.subplots(figsize=(9, 3.5))
            bal_vals = acct_ledger["Balance"].tolist()
            ax_gl.plot(range(len(bal_vals)), bal_vals, marker=".", linewidth=1.5, color="#4e79a7")
            ax_gl.fill_between(range(len(bal_vals)), bal_vals, alpha=0.1, color="#4e79a7")
            ax_gl.set_ylabel("Balance ($)")
            ax_gl.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
            ax_gl.set_xlabel("Transaction #")
            ax_gl.set_title(f"Account {selected_acct} — Running Balance")
            plt.tight_layout()
            st.pyplot(fig_gl)
            plt.close(fig_gl)

        # Monthly summary for this account
        monthly_summary = build_monthly_gl_summary(daily_device_hours=daily_hours, price_per_hour=price)
        acct_monthly = monthly_summary[monthly_summary["Account #"] == selected_acct]
        if not acct_monthly.empty:
            st.divider()
            st.markdown("### Monthly Activity Summary")
            display_monthly = acct_monthly[["Month", "Total Debits", "Total Credits", "Ending Balance"]].copy()
            display_monthly["Total Debits"] = display_monthly["Total Debits"].apply(
                lambda x: f"${x:,.2f}" if x > 0 else "")
            display_monthly["Total Credits"] = display_monthly["Total Credits"].apply(
                lambda x: f"${x:,.2f}" if x > 0 else "")
            display_monthly["Ending Balance"] = display_monthly["Ending Balance"].apply(
                lambda x: f"${x:,.2f}")
            st.dataframe(display_monthly, use_container_width=True, hide_index=True)

    # ---- TRIAL BALANCE ----
    elif acct_section == "Trial Balance":
        st.markdown("### Trial Balance — Year 1 Ending")
        st.caption(
            "The Trial Balance lists every GL account with its ending debit or credit balance. "
            "Total Debits MUST equal Total Credits — this proves the books are in balance. "
            "The TB is the checkpoint between the GL and financial statements."
        )

        tb_df = build_trial_balance(daily_device_hours=daily_hours, price_per_hour=price)
        tb_valid = validate_trial_balance(tb_df)

        # Balance check badge
        if tb_valid["is_balanced"]:
            st.markdown(
                "<div style='background:#d4edda;padding:12px;border-radius:8px;"
                "border-left:6px solid #155724;margin-bottom:16px;'>"
                "<div style='font-size:18px;font-weight:700;color:#155724;'>"
                "TRIAL BALANCE IS IN BALANCE</div>"
                f"<div style='color:#155724;'>Total Debits: ${tb_valid['total_debits']:,.2f} = "
                f"Total Credits: ${tb_valid['total_credits']:,.2f}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background:#f8d7da;padding:12px;border-radius:8px;"
                "border-left:6px solid #721c24;margin-bottom:16px;'>"
                "<div style='font-size:18px;font-weight:700;color:#721c24;'>"
                "TRIAL BALANCE OUT OF BALANCE</div>"
                f"<div style='color:#721c24;'>Debits: ${tb_valid['total_debits']:,.2f} | "
                f"Credits: ${tb_valid['total_credits']:,.2f} | "
                f"Difference: ${tb_valid['difference']:,.2f}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # Summary metrics
        tb_m1, tb_m2, tb_m3 = st.columns(3)
        tb_m1.metric("Total Debits", f"${tb_valid['total_debits']:,.2f}")
        tb_m2.metric("Total Credits", f"${tb_valid['total_credits']:,.2f}")
        tb_m3.metric("Accounts with Balances",
                     f"{sum(1 for _, r in tb_df.iterrows() if r['Debit'] > 0 or r['Credit'] > 0)}")

        st.divider()

        # Trial Balance table
        display_tb = tb_df.copy()

        def color_tb_type(val):
            type_colors_tb = {
                "Asset": "color: #4e79a7; font-weight: bold",
                "Liability": "color: #e15759; font-weight: bold",
                "Equity": "color: #59a14f; font-weight: bold",
                "Revenue": "color: #76b7b2; font-weight: bold",
                "Expense": "color: #f28e2b; font-weight: bold",
            }
            return type_colors_tb.get(val, "")

        # Format numbers
        display_tb["Debit"] = display_tb["Debit"].apply(
            lambda x: f"${x:,.2f}" if x > 0 else "")
        display_tb["Credit"] = display_tb["Credit"].apply(
            lambda x: f"${x:,.2f}" if x > 0 else "")

        styled_tb = display_tb.style.map(color_tb_type, subset=["Type"])
        st.dataframe(styled_tb, use_container_width=True, hide_index=True, height=700)

        # Totals row
        st.markdown(
            f"<div style='background:#f0f0f0;padding:10px;border-radius:4px;font-family:monospace;'>"
            f"<b>TOTALS</b> &nbsp;&nbsp;&nbsp; "
            f"Debits: <b>${tb_valid['total_debits']:,.2f}</b> &nbsp;&nbsp; "
            f"Credits: <b>${tb_valid['total_credits']:,.2f}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Visual: balance composition
        st.divider()
        st.markdown("### Trial Balance Composition")
        tb_by_type = tb_df.groupby("Type").agg(
            Debits=("Debit", "sum"),
            Credits=("Credit", "sum"),
        )

        fig_tb_comp, ax_tb_comp = plt.subplots(figsize=(8, 4))
        x_pos_tb = range(len(tb_by_type))
        width_tb = 0.35
        ax_tb_comp.bar([p - width_tb/2 for p in x_pos_tb], tb_by_type["Debits"],
                      width=width_tb, label="Debits", color="#4e79a7")
        ax_tb_comp.bar([p + width_tb/2 for p in x_pos_tb], tb_by_type["Credits"],
                      width=width_tb, label="Credits", color="#e15759")
        ax_tb_comp.set_xticks(list(x_pos_tb))
        ax_tb_comp.set_xticklabels(tb_by_type.index.tolist())
        ax_tb_comp.set_ylabel("Amount ($)")
        ax_tb_comp.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax_tb_comp.legend()
        ax_tb_comp.set_title("Trial Balance — Debits vs Credits by Account Type")
        plt.tight_layout()
        st.pyplot(fig_tb_comp)
        plt.close(fig_tb_comp)

    # ---- GL → FINANCIAL STATEMENTS ----
    elif acct_section == "GL → Financial Statements":
        st.markdown("### GL → Financial Statement Mapping")
        st.caption(
            "This shows exactly how each GL account rolls into the Income Statement "
            "or Balance Sheet. The accounting system PRODUCES the financial statements — "
            "this is the bridge."
        )

        fs_map = build_fs_mapping(daily_device_hours=daily_hours, price_per_hour=price)
        totals_fs = fs_map["totals"]

        # GAAP flow diagram
        st.markdown(
            "<div style='background:#f8f9fa;padding:16px;border-radius:8px;"
            "border:1px solid #dee2e6;margin-bottom:16px;font-family:monospace;'>"
            "<div style='font-weight:700;font-size:14px;margin-bottom:8px;'>GAAP Accounting Flow</div>"
            "<div>Transactions → <b>Journal Entries</b> (debits & credits)</div>"
            "<div>&nbsp;&nbsp;&nbsp;&nbsp;→ Post to <b>General Ledger</b> (running balances)</div>"
            "<div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→ <b>Trial Balance</b> (DR = CR check)</div>"
            "<div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "→ <b>Income Statement</b> (Revenue & Expense accounts)</div>"
            "<div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "→ <b>Balance Sheet</b> (Asset, Liability & Equity accounts)</div>"
            "<div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "→ <b>Cash Flow Statement</b> (derived from BS changes + IS)</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Income Statement mapping
        st.markdown("### Income Statement (from Revenue & Expense Accounts)")
        is_rows = []
        for item in fs_map["income_statement"]:
            acct_type = CHART_OF_ACCOUNTS[item["Account #"]]["type"]
            sign = -1 if acct_type == "revenue" else 1  # revenue is positive on IS
            is_rows.append({
                "Account #": item["Account #"],
                "Account Name": item["Account Name"],
                "FS Line": item["FS Line"],
                "GL Balance": item["Balance"],
                "IS Impact": -item["Balance"] if acct_type == "revenue" else item["Balance"],
            })

        is_map_df = pd.DataFrame(is_rows)

        # Summary metrics
        is_c1, is_c2, is_c3, is_c4, is_c5 = st.columns(5)
        is_c1.metric("Revenue", f"${totals_fs['total_revenue']:,.0f}")
        is_c2.metric("Gross Profit", f"${totals_fs['gross_profit']:,.0f}")
        is_c3.metric("EBITDA", f"${totals_fs['ebitda']:,.0f}")
        is_c4.metric("EBIT", f"${totals_fs['ebit']:,.0f}")
        is_c5.metric("Pre-Tax Income", f"${totals_fs['pretax_income']:,.0f}")

        display_is_map = is_map_df.copy()
        display_is_map["GL Balance"] = display_is_map["GL Balance"].apply(lambda x: f"${x:,.2f}")

        def color_is_impact(val):
            if isinstance(val, (int, float)):
                return "color: #59a14f" if val < 0 else "color: #e15759"
            return ""

        display_is_map["IS Impact"] = display_is_map["IS Impact"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(display_is_map, use_container_width=True, hide_index=True)

        st.divider()

        # Balance Sheet mapping
        st.markdown("### Balance Sheet (from Asset, Liability & Equity Accounts)")

        bs_c1, bs_c2, bs_c3 = st.columns(3)
        bs_c1.metric("Total Assets", f"${totals_fs['total_assets']:,.0f}")
        bs_c2.metric("Total Liabilities", f"${totals_fs['total_liabilities']:,.0f}")
        bs_c3.metric("Total Equity", f"${totals_fs['total_equity']:,.0f}")

        bs_map_rows = []
        for item in fs_map["balance_sheet"]:
            bs_map_rows.append({
                "Account #": item["Account #"],
                "Account Name": item["Account Name"],
                "Type": CHART_OF_ACCOUNTS[item["Account #"]]["type"].title(),
                "FS Line": item["FS Line"],
                "Ending Balance": item["Balance"],
            })

        bs_map_df = pd.DataFrame(bs_map_rows)
        display_bs_map = bs_map_df.copy()
        display_bs_map["Ending Balance"] = display_bs_map["Ending Balance"].apply(
            lambda x: f"${x:,.2f}" if x > 0 else "")

        def color_bs_type(val):
            bs_colors = {
                "Asset": "color: #4e79a7; font-weight: bold",
                "Liability": "color: #e15759; font-weight: bold",
                "Equity": "color: #59a14f; font-weight: bold",
            }
            return bs_colors.get(val, "")

        styled_bs_map = display_bs_map.style.map(color_bs_type, subset=["Type"])
        st.dataframe(styled_bs_map, use_container_width=True, hide_index=True)

        # Accounting equation check
        st.divider()
        a_eq = totals_fs["total_assets"]
        le_eq = totals_fs["total_liabilities"] + totals_fs["total_equity"]
        # Note: need to add net income to equity for full balance
        le_eq_with_ni = le_eq + totals_fs["pretax_income"]
        eq_balanced = abs(a_eq - le_eq_with_ni) < 1.0

        st.markdown("### Accounting Equation Check")
        st.caption("Assets = Liabilities + Equity + Net Income (before closing)")

        if eq_balanced:
            st.markdown(
                f"<div style='background:#d4edda;padding:14px;border-radius:8px;"
                f"border-left:6px solid #155724;'>"
                f"<div style='font-size:16px;font-weight:700;color:#155724;'>"
                f"BALANCED: Assets ${a_eq:,.0f} = L+E+NI ${le_eq_with_ni:,.0f}</div>"
                f"<div style='color:#155724;font-size:13px;'>"
                f"Assets: ${a_eq:,.0f} | Liabilities: ${totals_fs['total_liabilities']:,.0f} | "
                f"Equity: ${totals_fs['total_equity']:,.0f} | "
                f"Net Income: ${totals_fs['pretax_income']:,.0f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#f8d7da;padding:14px;border-radius:8px;"
                f"border-left:6px solid #721c24;'>"
                f"<div style='font-size:16px;font-weight:700;color:#721c24;'>"
                f"OUT OF BALANCE: Assets ${a_eq:,.0f} ≠ L+E+NI ${le_eq_with_ni:,.0f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Visual: waterfall from GL to financial statements
        st.divider()
        st.markdown("### Income Statement Buildup (from GL)")
        buildup_labels = ["Revenue", "(-) COGS", "Gross Profit", "(-) OpEx", "EBITDA",
                         "(-) Depreciation", "EBIT", "(-) Interest", "Pre-Tax Income"]
        buildup_values = [
            totals_fs["total_revenue"],
            -totals_fs["total_cogs"],
            totals_fs["gross_profit"],
            -totals_fs["total_opex"],
            totals_fs["ebitda"],
            -totals_fs["depreciation"],
            totals_fs["ebit"],
            -totals_fs["interest"],
            totals_fs["pretax_income"],
        ]
        buildup_colors = ["#59a14f" if v >= 0 else "#e15759" for v in buildup_values]

        fig_buildup, ax_buildup = plt.subplots(figsize=(10, 4.5))
        ax_buildup.bar(buildup_labels, buildup_values, color=buildup_colors, width=0.6)
        ax_buildup.axhline(y=0, color="gray", linewidth=0.8, linestyle="--")
        ax_buildup.set_ylabel("Amount ($)")
        ax_buildup.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax_buildup.set_title("Income Statement Buildup — From GL Account Balances")
        plt.xticks(rotation=25, ha="right", fontsize=9)
        plt.tight_layout()
        st.pyplot(fig_buildup)
        plt.close(fig_buildup)


# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.caption(
    "Gaming Arena Financial Model Toolkit  |  "
    "Built with Python, pandas, and Streamlit  |  "
    "Data from config.py -> model_engine.py -> dashboard.py"
)
