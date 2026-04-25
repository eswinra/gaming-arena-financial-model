"""
MODULE 6: MAIN RUNNER
=======================
Gaming Arena, LLC — Command-Line Interface

WHAT THIS FILE TEACHES YOU:
- argparse (building command-line tools)
- Running different modes from a single entry point
- How Python packages/projects are structured
- The if __name__ == "__main__" pattern (again, because it's important)

HOW TO USE:
  python main.py                    → Run the full model and print results
  python main.py --mode model       → Same as above
  python main.py --mode scenarios   → Run scenario comparison
  python main.py --mode sensitivity → Build sensitivity table
  python main.py --mode excel       → Generate Excel workbook
  python main.py --mode montecarlo  → Run Monte Carlo simulation
  python main.py --mode accounting  → Show GL, trial balance, FS mapping
  python main.py --mode all         → Run everything and export Excel

  python main.py --hours 120        → Override daily device-hours
  python main.py --price 10.00      → Override price per hour
  python main.py --years 5          → Override forecast period

PYTHON CONCEPT: argparse
  argparse lets you accept command-line arguments. Instead of editing code
  to change inputs, you pass them when you run the script.
  This is how most professional Python tools work.
"""

import argparse
import sys


def main():
    # =========================================================================
    # ARGUMENT PARSING
    # =========================================================================
    parser = argparse.ArgumentParser(
        description="Gaming Arena Financial Model Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          Full model printout
  python main.py --mode excel             Generate Excel workbook
  python main.py --hours 120 --price 10   Custom scenario
  python main.py --mode all               Everything + Excel export
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["model", "scenarios", "sensitivity", "excel", "montecarlo",
                 "variance", "forecast", "uniteconomics", "executive",
                 "dcf", "integrity", "accounting", "all"],
        default="model",
        help="What to run (default: model)",
    )
    parser.add_argument("--hours", type=int, default=None, help="Daily device-hours (default: 100)")
    parser.add_argument("--price", type=float, default=None, help="Price per hour (default: 9.00)")
    parser.add_argument("--years", type=int, default=None, help="Forecast years (default: 3)")
    parser.add_argument("--sims", type=int, default=1000, help="Monte Carlo simulations (default: 1000)")
    parser.add_argument("--output", type=str, default="Gaming_Arena_Financial_Model.xlsx", help="Excel output filename")

    args = parser.parse_args()

    # =========================================================================
    # IMPORT MODULES (after parsing, so --help is fast)
    # =========================================================================
    # PYTHON CONCEPT: Lazy imports. We don't import heavy libraries (pandas, numpy)
    # until we know we need them. This makes --help respond instantly.
    from config import ASSUMPTIONS, calc_utilization
    from model_engine import build_full_model
    from scenarios import (
        run_scenario_comparison,
        build_sensitivity_table,
        find_breakeven_hours,
        run_monte_carlo,
        summarize_monte_carlo,
    )

    hours = args.hours or ASSUMPTIONS["utilization"]["base_case_hours"]
    price = args.price or ASSUMPTIONS["pricing"]["price_per_hour"]
    years = args.years or ASSUMPTIONS["model"]["forecast_years"]

    print("=" * 70)
    print("GAMING ARENA, LLC — FINANCIAL MODEL TOOLKIT")
    print("=" * 70)
    print(f"  Daily Hours: {hours}  |  Price: ${price:.2f}/hr  |  "
          f"Utilization: {calc_utilization(hours):.1%}  |  Years: {years}")
    print("=" * 70)

    # =========================================================================
    # MODE: MODEL
    # =========================================================================
    if args.mode in ("model", "all"):
        print("\n--- 3-STATEMENT FINANCIAL MODEL ---")
        print("-" * 70)

        model = build_full_model(
            daily_device_hours=hours,
            price_per_hour=price,
            forecast_years=years,
        )

        # Print Income Statement highlights
        inc = model["income_statement"]
        print("\nIncome Statement Highlights:")
        for metric in ["Total Revenue", "Gross Profit", "EBITDA", "Pre-Tax Income"]:
            vals = "  ".join(f"${inc.loc[metric, c]:>12,.0f}" for c in inc.columns)
            print(f"  {metric:<28s} {vals}")

        # Print Ratios
        ratios = model["ratios"]
        print("\nKey Ratios:")
        for metric in ratios.index:
            vals = "  ".join(
                f"{ratios.loc[metric, c]:>12.1%}" if "Margin" in metric or "Return" in metric
                else f"{ratios.loc[metric, c]:>11.2f}x" if "DSCR" in metric or "Debt" in metric
                else f"${ratios.loc[metric, c]:>12,.0f}" if "Cash" in metric
                else f"{ratios.loc[metric, c]:>12.1f}"
                for c in ratios.columns
            )
            print(f"  {metric:<28s} {vals}")

        # Balance check
        bs = model["balance_sheet"]
        print("\nBalance Sheet Verification:")
        for label in bs.columns:
            check = bs.loc["Balance Check Passes", label]
            print(f"  {label}: {'PASSES' if check else 'FAILS'}")

    # =========================================================================
    # MODE: SCENARIOS
    # =========================================================================
    if args.mode in ("scenarios", "all"):
        print("\n\n--- SCENARIO COMPARISON ---")
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

        # Breakeven
        print("\n  Breakeven Analysis:")
        be = find_breakeven_hours("Pre-Tax Income", 0, price_per_hour=price)
        print(f"    Pre-Tax breakeven: {be['breakeven_daily_hours']} hrs/day "
              f"({be['utilization_at_breakeven']:.1%} utilization)")
        be_dscr = find_breakeven_hours("DSCR", 1.25, price_per_hour=price)
        print(f"    SBA minimum DSCR:  {be_dscr['breakeven_daily_hours']} hrs/day "
              f"({be_dscr['utilization_at_breakeven']:.1%} utilization)")

    # =========================================================================
    # MODE: SENSITIVITY
    # =========================================================================
    if args.mode in ("sensitivity", "all"):
        print("\n\n--- SENSITIVITY TABLE — EBITDA ---")
        print("-" * 70)
        sens = build_sensitivity_table("EBITDA")
        formatted = sens.map(lambda x: f"${x:>10,.0f}" if x is not None else "")
        print(formatted.to_string())

    # =========================================================================
    # MODE: MONTE CARLO
    # =========================================================================
    if args.mode in ("montecarlo", "all"):
        print(f"\n\n--- MONTE CARLO SIMULATION ({args.sims:,} runs) ---")
        print("-" * 70)
        sim_df = run_monte_carlo(n_simulations=args.sims)
        summary = summarize_monte_carlo(sim_df)

        print(f"  Expected Revenue:       ${summary['revenue']['mean']:>12,.0f}")
        print(f"  Expected EBITDA:        ${summary['ebitda']['mean']:>12,.0f}")
        print(f"  Expected Pre-Tax:       ${summary['pretax_income']['mean']:>12,.0f}")
        print(f"  Probability of Loss:    {summary['probability_of_loss']:>12.1%}")
        if summary.get("probability_dscr_below_125") is not None:
            print(f"  P(DSCR < 1.25x):       {summary['probability_dscr_below_125']:>12.1%}")
        if summary.get("dscr") and summary["dscr"].get("mean") is not None:
            print(f"  Expected DSCR:          {summary['dscr']['mean']:>12.2f}x")
        print(f"  EBITDA Range (5-95%):   ${summary['ebitda']['p5']:>10,.0f} to "
              f"${summary['ebitda']['p95']:>,.0f}")

    # =========================================================================
    # MODE: VARIANCE
    # =========================================================================
    if args.mode in ("variance", "all"):
        print("\n\n--- BUDGET VS ACTUAL VARIANCE ---")
        print("-" * 70)
        from variance_analysis import (
            build_budget, build_actuals, compute_variance,
            generate_variance_commentary, build_kpi_scorecard,
        )
        budget = build_budget(daily_device_hours=hours, price_per_hour=price)
        for scenario_name in ["Worst Case", "Base Case", "Best Case"]:
            actuals_data = build_actuals(
                daily_device_hours=hours, price_per_hour=price, scenario=scenario_name,
            )
            variance = compute_variance(budget, actuals_data)
            print(f"\n  [{scenario_name}] Pre-Tax Variance: "
                  f"${variance.loc['Pre-Tax Income', 'Variance ($)']:+,.0f} "
                  f"({variance.loc['Pre-Tax Income', 'Variance (%)']:+.1%})")
            commentary = generate_variance_commentary(variance, top_n=3)
            for c in commentary:
                print(f"    - {c}")

    # =========================================================================
    # MODE: ROLLING FORECAST
    # =========================================================================
    if args.mode in ("forecast", "all"):
        print("\n\n--- ROLLING FORECAST (closed through month 6) ---")
        print("-" * 70)
        from rolling_forecast import (
            build_rolling_forecast, summarize_latest_estimate,
            compute_forecast_accuracy, summarize_forecast_accuracy,
        )
        rf = build_rolling_forecast(
            daily_device_hours=hours, price_per_hour=price,
            scenario="Base Case", close_through_month=6,
        )
        le = summarize_latest_estimate(rf)
        for metric, row in le.iterrows():
            print(f"  {metric:20s}  Budget: ${row['Full-Year Budget']:>10,.0f}  "
                  f"LE: ${row['Latest Estimate']:>10,.0f}  "
                  f"Var: ${row['Variance ($)']:>+10,.0f} ({row['Variance (%)']:>+.1%})")

        acc = compute_forecast_accuracy(
            daily_device_hours=hours, price_per_hour=price, scenario="Base Case",
        )
        acc_summary = summarize_forecast_accuracy(acc)
        print("\n  Forecast Accuracy:")
        for metric, row in acc_summary.iterrows():
            print(f"    {metric:12s}  MAPE: {row['MAPE']:.1%} [{row['Grade']}]  "
                  f"Bias: ${row['Avg Bias ($)']:>+8,.0f}")

    # =========================================================================
    # MODE: UNIT ECONOMICS
    # =========================================================================
    if args.mode in ("uniteconomics", "all"):
        print("\n\n--- UNIT ECONOMICS ---")
        print("-" * 70)
        from unit_economics import compute_unit_economics, build_driver_sensitivity
        ue = compute_unit_economics(daily_device_hours=hours, price_per_hour=price)
        for group, items in ue.items():
            print(f"\n  {group}:")
            for m in items:
                if m["Unit"] == "$":
                    print(f"    {m['Metric']:40s}  ${m['Value']:>10,.2f}")
                elif m["Unit"] == "%":
                    print(f"    {m['Metric']:40s}  {m['Value']:>10.1%}")
                else:
                    print(f"    {m['Metric']:40s}  {m['Value']:>10.1f} {m['Unit']}")

        print("\n  Driver Sensitivity (±10%):")
        sens = build_driver_sensitivity(daily_device_hours=hours, price_per_hour=price)
        for driver, row in sens.iterrows():
            print(f"    {driver:30s}  EBITDA: ${row['New EBITDA']:>10,.0f}  "
                  f"Impact: ${row['EBITDA Impact ($)']:>+8,.0f} ({row['EBITDA Impact (%)']:>+.1%})")

    # =========================================================================
    # MODE: EXECUTIVE SUMMARY
    # =========================================================================
    if args.mode in ("executive", "all"):
        print("\n\n--- EXECUTIVE SUMMARY ---")
        print("-" * 70)
        from executive_summary import generate_executive_summary
        exec_summary = generate_executive_summary(
            daily_device_hours=hours, price_per_hour=price,
            forecast_years=years,
        )
        print(f"\n  [{exec_summary['overall_status']}] {exec_summary['headline']}")
        for section in exec_summary["sections"]:
            print(f"\n  [{section['status']:>5s}] {section['title']}")
            words = section["narrative"].split()
            line = "    "
            for word in words:
                if len(line) + len(word) > 78:
                    print(line)
                    line = "    "
                line += word + " "
            if line.strip():
                print(line)
        if exec_summary["risks"]:
            print("\n  RISKS:")
            for r in exec_summary["risks"]:
                print(f"    [{r['severity']:>6s}] {r['risk']}: {r['detail']}")
        print("\n  RECOMMENDATIONS:")
        for i, rec in enumerate(exec_summary["recommendations"], 1):
            print(f"    {i}. {rec}")

    # =========================================================================
    # MODE: DCF VALUATION
    # =========================================================================
    if args.mode in ("dcf", "all"):
        print("\n\n--- DCF BUSINESS VALUATION ---")
        print("-" * 70)
        from dcf_valuation import build_dcf_valuation, build_dcf_sensitivity
        dcf = build_dcf_valuation(
            daily_device_hours=hours, price_per_hour=price,
            forecast_years=5, wacc=0.12, terminal_growth_rate=0.02,
        )
        print(f"  PV of UFCFs:          ${dcf['pv_ufcf_total']:>12,.0f}")
        print(f"  PV of Terminal Value:  ${dcf['pv_terminal']:>12,.0f}")
        print(f"  Enterprise Value:     ${dcf['enterprise_value']:>12,.0f}")
        print(f"  Less: Net Debt:       ${dcf['net_debt']:>12,.0f}")
        print(f"  Equity Value:         ${dcf['equity_value']:>12,.0f}")
        print(f"\n  EV/EBITDA:            {dcf['metrics']['ev_to_ebitda']:>12.1f}x")
        print(f"  ROI on Equity:        {dcf['metrics']['roi_on_equity']:>12.1%}")
        print(f"  ROI on Investment:    {dcf['metrics']['roi_on_total_investment']:>12.1%}")
        print(f"  TV as % of EV:        {dcf['metrics']['tv_as_pct_of_ev']:>12.1%}")

        print("\n  Sensitivity (Equity Value — WACC vs Growth):")
        sens_dcf = build_dcf_sensitivity(
            daily_device_hours=hours, price_per_hour=price, forecast_years=5,
        )
        formatted_dcf = sens_dcf.map(
            lambda x: f"${x:>10,.0f}" if isinstance(x, (int, float)) and x != float('inf') else "N/A"
        )
        print(formatted_dcf.to_string())

    # =========================================================================
    # MODE: MODEL INTEGRITY
    # =========================================================================
    if args.mode in ("integrity", "all"):
        print("\n\n--- MODEL INTEGRITY CHECKS ---")
        print("-" * 70)
        from model_integrity import run_integrity_checks, summarize_integrity
        checks = run_integrity_checks(
            daily_device_hours=hours, price_per_hour=price,
            forecast_years=years,
        )
        summary_ic = summarize_integrity(checks)
        print(f"  Overall: {summary_ic['overall']}")
        print(f"  Passed: {summary_ic['passed']} | Failed: {summary_ic['failed']} | "
              f"Warnings: {summary_ic['warnings']} | Pass Rate: {summary_ic['pass_rate']:.0%}")
        for c in checks:
            icon = "PASS" if c["Status"] == "PASS" else "FAIL" if c["Status"] == "FAIL" else "WARN"
            if c["Status"] != "PASS":
                print(f"  [{icon}] {c['Check']}: {c['Detail']}")

    # =========================================================================
    # MODE: ACCOUNTING
    # =========================================================================
    if args.mode in ("accounting", "all"):
        print("\n\n--- ACCOUNTING & GENERAL LEDGER ---")
        print("-" * 70)
        from accounting_engine import (
            get_chart_of_accounts_df, get_journal_entries_df,
            build_trial_balance, validate_trial_balance, build_fs_mapping,
        )

        # Chart of Accounts summary
        coa = get_chart_of_accounts_df()
        print(f"\n  Chart of Accounts: {len(coa)} accounts")
        for acct_type in ["Asset", "Liability", "Equity", "Revenue", "Expense"]:
            count = len(coa[coa["Type"] == acct_type])
            print(f"    {acct_type:<12s}: {count} accounts")

        # Journal Entries summary
        je_df = get_journal_entries_df(daily_device_hours=hours, price_per_hour=price)
        n_entries = je_df["JE #"].nunique()
        print(f"\n  Journal Entries: {n_entries} entries, {len(je_df)} lines")
        print(f"    Total Debits:  ${je_df['Debit'].sum():>12,.2f}")
        print(f"    Total Credits: ${je_df['Credit'].sum():>12,.2f}")

        # Trial Balance
        tb = build_trial_balance(daily_device_hours=hours, price_per_hour=price)
        tb_valid = validate_trial_balance(tb)
        print(f"\n  Trial Balance: {'BALANCED' if tb_valid['is_balanced'] else 'OUT OF BALANCE'}")
        print(f"    Debits:  ${tb_valid['total_debits']:>12,.2f}")
        print(f"    Credits: ${tb_valid['total_credits']:>12,.2f}")

        # FS Mapping
        fs = build_fs_mapping(daily_device_hours=hours, price_per_hour=price)
        t = fs["totals"]
        print(f"\n  GL → Financial Statements:")
        print(f"    Revenue:        ${t['total_revenue']:>12,.2f}")
        print(f"    Gross Profit:   ${t['gross_profit']:>12,.2f}")
        print(f"    EBITDA:         ${t['ebitda']:>12,.2f}")
        print(f"    Pre-Tax Income: ${t['pretax_income']:>12,.2f}")

    # =========================================================================
    # MODE: EXCEL
    # =========================================================================
    if args.mode in ("excel", "all"):
        print("\n\n--- GENERATING EXCEL REPORT ---")
        print("-" * 70)
        from excel_export import generate_excel_report
        generate_excel_report(args.output)

    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
