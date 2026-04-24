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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Income Statement",
    "Cash Flow & Balance Sheet",
    "Scenarios",
    "Sensitivity",
    "Monte Carlo",
    "Breakeven",
])

# --- TAB 1: Income Statement ---
with tab1:
    st.subheader("Projected Income Statement")

    # Format the DataFrame for display
    # PYTHON CONCEPT: .map() applies a function to every cell
    display_inc = inc.copy()
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
        display_cf = cf.copy()
        for col in display_cf.columns:
            display_cf[col] = display_cf[col].apply(
                lambda x: "" if pd.isna(x)
                else f"${x:,.0f}" if isinstance(x, (int, float))
                else str(x)
            )
        st.dataframe(display_cf, use_container_width=True)

    with c2:
        st.subheader("Key Ratios")
        display_ratios = ratios.copy()
        for col in display_ratios.columns:
            display_ratios[col] = display_ratios[col].apply(
                lambda x: f"{x:.1%}" if isinstance(x, float) and abs(x) < 2
                else f"{x:.2f}x" if isinstance(x, float) and abs(x) < 50
                else f"${x:,.0f}" if isinstance(x, (int, float))
                else ""
            )
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

    # Format for display
    display_comp = comparison.copy()
    for col in display_comp.columns:
        display_comp[col] = display_comp[col].apply(
            lambda x: f"{x:.1%}" if isinstance(x, float) and abs(x) < 1
            else f"{x:.2f}x" if isinstance(x, float) and 1 <= abs(x) < 10
            else f"${x:,.0f}" if isinstance(x, (int, float)) and abs(x) >= 10
            else f"{x:.0f}" if isinstance(x, (int, float))
            else str(x)
        )
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
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Expected EBITDA", f"${summary['ebitda']['mean']:,.0f}")
    m2.metric("Probability of Loss", f"{summary['probability_of_loss']:.1%}")
    m3.metric("EBITDA 5th Pctl", f"${summary['ebitda']['p5']:,.0f}")
    m4.metric("EBITDA 95th Pctl", f"${summary['ebitda']['p95']:,.0f}")

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

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.caption(
    "Gaming Arena Financial Model Toolkit  |  "
    "Built with Python, pandas, and Streamlit  |  "
    "Data from config.py → model_engine.py → dashboard.py"
)
