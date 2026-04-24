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
        choices=["model", "scenarios", "sensitivity", "excel", "montecarlo", "all"],
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
        print(f"  EBITDA Range (5-95%):   ${summary['ebitda']['p5']:>10,.0f} to "
              f"${summary['ebitda']['p95']:>,.0f}")

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
