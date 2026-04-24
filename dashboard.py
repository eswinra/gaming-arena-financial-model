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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "Income Statement",
    "Cash Flow & Balance Sheet",
    "Scenarios",
    "Sensitivity",
    "Monte Carlo",
    "Breakeven",
    "Variance Analysis",
    "KPI Scorecard",
    "Cost Drivers",
    "Assumptions Lab",
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

# --- TAB 7: Variance Analysis ---
with tab7:
    st.subheader("Budget vs Actual Variance Analysis")

    # Import scenario descriptions for display
    from variance_analysis import VARIANCE_SCENARIOS
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
    # DSCR impact
    annual_ds = a["debt"]["annual_principal_payment"] + interest
    adj_dscr = (adj_pretax + depreciation) / annual_ds if annual_ds > 0 else 0
    orig_dscr = (orig_pretax + depreciation) / annual_ds if annual_ds > 0 else 0
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
    display_adj_inc = adj_inc.copy()
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

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.caption(
    "Gaming Arena Financial Model Toolkit  |  "
    "Built with Python, pandas, and Streamlit  |  "
    "Data from config.py -> model_engine.py -> dashboard.py"
)
