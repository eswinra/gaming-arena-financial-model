# Gaming Arena Financial Modeling Toolkit

A Python-based financial modeling and automation toolkit built around the Gaming Arena, LLC business model. Designed as a hands-on learning project for applying Python to real financial analysis.

## Project Structure

```
gaming_arena_financial_toolkit/
├── config.py          Module 1: Assumptions & data layer
├── model_engine.py    Module 2: 3-statement model (IS → CF → BS)
├── scenarios.py       Module 3: Scenario, sensitivity, Monte Carlo
├── excel_export.py    Module 4: Automated Excel report generation
├── dashboard.py       Module 5: Interactive Streamlit dashboard
├── main.py            Module 6: CLI runner (ties everything together)
└── README.md          This file
```

## How to Use

### Setup
```bash
pip install pandas numpy openpyxl streamlit
```

### Run the Model (CLI)
```bash
python main.py                           # Base case model
python main.py --mode all                # Everything + Excel export
python main.py --hours 120 --price 10    # Custom scenario
python main.py --mode scenarios          # Scenario comparison
python main.py --mode sensitivity        # Sensitivity table
python main.py --mode montecarlo         # Monte Carlo simulation
python main.py --mode excel              # Generate Excel workbook
```

### Run the Dashboard
```bash
streamlit run dashboard.py
```

### Run Individual Modules
Each module has a self-test. Run it directly to see what it does:
```bash
python config.py          # Validate assumptions
python model_engine.py    # Print 3-statement model
python scenarios.py       # Scenario + sensitivity + Monte Carlo
python excel_export.py    # Generate Excel report
```

## What Each Module Teaches

| Module | File | Python Concepts | Finance Concepts |
|--------|------|----------------|-----------------|
| 1 | config.py | Dictionaries, tuples, type hints, functions | Assumption management, audit trail |
| 2 | model_engine.py | pandas DataFrames, functions, imports | IS/CF/BS linkage, EBITDA, DSCR |
| 3 | scenarios.py | Loops, numpy, binary search | Scenario analysis, sensitivity, breakeven |
| 4 | excel_export.py | openpyxl, formatting, file I/O | Professional model formatting |
| 5 | dashboard.py | Streamlit, widgets, visualization | Interactive financial dashboards |
| 6 | main.py | argparse, CLI tools, project structure | Putting it all together |

## Business Model Summary

- **Business**: 40-station gaming arena (24 PCs, 16 consoles)
- **Revenue**: $9/hr per device, 100 device-hrs/day base case (20.8% utilization)
- **Total Project Cost**: $200,000 (90% SBA loan, 10% owner equity)
- **Year 1 EBITDA**: $42,052 (base case)
- **DSCR**: 1.50x (above SBA 1.25x minimum)

## Next Steps for Learning

After working through these modules, consider extending the project:

1. **Add monthly granularity** — break Year 1 into 12 months with seasonal patterns
2. **Connect to real data** — import actual POS data from Square API
3. **Add a loan amortization schedule** — model declining interest, increasing principal
4. **Build a multi-location model** — forecast expansion to Location 2 and 3
5. **Add tax logic** — incorporate federal/state tax rates and calculate after-tax income
6. **PDF report generation** — auto-generate investor-ready PDF reports with charts
