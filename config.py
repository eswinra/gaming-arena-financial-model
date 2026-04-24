"""
MODULE 1: ASSUMPTIONS & DATA LAYER
====================================
Gaming Arena, LLC — Financial Model Configuration

WHAT THIS FILE TEACHES YOU:
- Python dictionaries (nested key-value data structures)
- Constants vs. variables (what changes vs. what doesn't)
- Clean assumption management (one source of truth)
- Type hints (documenting what data types you expect)
- Why separating data from logic matters in financial modeling

HOW TO USE THIS FILE:
  from config import ASSUMPTIONS, STARTUP_COSTS, OPEX_BUDGET
  price = ASSUMPTIONS["pricing"]["price_per_hour"]

WHY THIS MATTERS:
  In Excel, assumptions are scattered across cells. In Python, you put them
  in one file. When you change an assumption here, every module that imports
  it automatically picks up the new value. No broken links, no missed cells.
"""

# =============================================================================
# BUSINESS ASSUMPTIONS
# =============================================================================
# These are the core drivers of the entire model. Everything downstream
# (revenue, expenses, cash flow) flows from these inputs.

ASSUMPTIONS = {
    # --- Capacity & Operations ---
    # These define what the business CAN do (capacity) vs. what we EXPECT (utilization)
    "capacity": {
        "total_devices": 40,              # 24 PCs + 16 consoles
        "pc_stations": 24,
        "console_stations": 16,
        "operating_hours_per_day": 12,    # 10 AM to 10 PM
        "days_per_year": 365,
        # MAX possible device-hours = 40 devices × 12 hours = 480 per day
        # This is your theoretical ceiling. You'll never hit 100%.
    },

    # --- Pricing ---
    "pricing": {
        "price_per_hour": 9.00,           # Pay-as-you-go rate per device-hour
        # NOTE: This is held constant across all 3 years in the base model.
        # In reality, you might raise prices 3-5% per year.
    },

    # --- Utilization Scenarios ---
    # Utilization = daily_device_hours / (total_devices × operating_hours)
    # This is the SINGLE MOST IMPORTANT DRIVER in the model.
    "utilization": {
        "worst_case_hours": 80,           # 80 / 480 = 16.7% utilization
        "base_case_hours": 100,           # 100 / 480 = 20.8% utilization
        "best_case_hours": 120,           # 120 / 480 = 25.0% utilization
    },

    # --- Growth ---
    "growth": {
        "annual_revenue_growth": 0.025,   # 2.5% — modest organic growth
        "annual_expense_growth": 0.025,   # 2.5% — inflation adjustment
        # Both at 2.5% means margins stay flat. Conservative.
    },

    # --- F&B / Merchandise ---
    "fnb": {
        "year1_revenue": 10_160,          # Food, beverage, merchandise sales
        "cogs_pct": 0.40,                 # 40% cost of goods on F&B
        # Underscore in 10_160 is Python syntax sugar — makes big numbers readable.
        # 10_160 == 10160. Use it.
    },

    # --- Fees ---
    "fees": {
        "merchant_processing_pct": 0.03,  # 3% of all revenue (Square fees)
    },

    # --- Debt / Loan ---
    "debt": {
        "loan_amount": 180_000,           # SBA 7(a) term loan
        "interest_rate": 0.10,            # 10% annual interest
        "annual_principal_payment": 10_000,
        "owner_equity": 20_000,           # 10% owner contribution
        "total_project_cost": 200_000,
    },

    # --- Depreciation ---
    "depreciation": {
        "depreciable_assets": 180_000,    # Property & equipment at cost
        "useful_life_years": 7,           # Simplified straight-line
        "annual_depreciation": 25_000,    # ~$180K / 7 years, rounded
        # NOTE: In real GAAP, you'd use MACRS or component depreciation.
        # This is simplified for the SBA application.
    },

    # --- Model Settings ---
    "model": {
        "forecast_years": 3,
        "year_labels": ["Year 1", "Year 2", "Year 3"],
    },
}


# =============================================================================
# STARTUP COSTS — DETAILED BREAKDOWN
# =============================================================================
# Each category is a dictionary with line items.
# This mirrors the "Use of Funds" from the SBA packet.

STARTUP_COSTS = {
    "gaming_pcs": {
        "label": "Gaming PCs (24 Units)",
        "items": {
            "CPU (Ryzen 5 7600 / i5-13400)": {"unit_cost": 260, "qty": 24},
            "GPU (RTX 4060 8GB)":             {"unit_cost": 450, "qty": 24},
            "Motherboard (B650/B760)":        {"unit_cost": 150, "qty": 24},
            "RAM (32GB DDR5)":                {"unit_cost": 90,  "qty": 24},
            "Storage (1TB NVMe SSD)":         {"unit_cost": 80,  "qty": 24},
            "Case (Mid-tower ATX)":           {"unit_cost": 80,  "qty": 24},
            "Power Supply (650W Gold)":       {"unit_cost": 90,  "qty": 24},
            "Cooling (CPU + case fans)":      {"unit_cost": 50,  "qty": 24},
            "Windows 11 Pro License":         {"unit_cost": 140, "qty": 24},
        },
        # LEARNING NOTE: This is a "nested dictionary." Each item has its own
        # dictionary with unit_cost and qty. You can calculate totals with:
        #   total = sum(v["unit_cost"] * v["qty"] for v in items.values())
    },
    "console_stations": {
        "label": "Console Stations (16 Units)",
        "items": {
            "PlayStation 5":      {"unit_cost": 500, "qty": 8},
            "Xbox Series X":     {"unit_cost": 500, "qty": 8},
            "Gaming Monitors":   {"unit_cost": 220, "qty": 16},
            "Console Accessories": {"unit_cost": 80, "qty": 16},
        },
    },
    "infrastructure": {
        "label": "Server & Networking",
        "items": {
            "Server Hardware":        {"unit_cost": 5_000, "qty": 1},
            "Network Equipment":      {"unit_cost": 4_000, "qty": 1},
            "Cabling & Installation": {"unit_cost": 3_000, "qty": 1},
            "Network Rack":           {"unit_cost": 1_500, "qty": 1},
            "Backup Systems (UPS)":   {"unit_cost": 1_500, "qty": 1},
        },
    },
    "security": {
        "label": "Security Systems",
        "items": {
            "Security Cameras":    {"unit_cost": 2_400, "qty": 1},
            "DVR/NVR System":      {"unit_cost": 1_500, "qty": 1},
            "Camera Installation": {"unit_cost": 1_200, "qty": 1},
            "PC Security Hardware": {"unit_cost": 1_600, "qty": 1},
            "Access Control":      {"unit_cost": 1_300, "qty": 1},
        },
    },
    "furniture_fixtures": {
        "label": "Furniture & Fixtures",
        "items": {
            "Gaming Desks (40)":       {"unit_cost": 160,   "qty": 40},
            "Gaming Chairs (40)":      {"unit_cost": 200,   "qty": 40},
            "PC Peripherals (24 sets)": {"unit_cost": 345,  "qty": 24},
            "TCG Tables & Seating":    {"unit_cost": 1_500, "qty": 1},
            "Display TVs":             {"unit_cost": 1_800, "qty": 1},
            "Merchandise Shelving":    {"unit_cost": 800,   "qty": 1},
            "Front Counter":           {"unit_cost": 1_200, "qty": 1},
            "Office Furniture":        {"unit_cost": 1_200, "qty": 1},
            "Storage Solutions":       {"unit_cost": 800,   "qty": 1},
        },
    },
    "build_out": {
        "label": "Interior Build-Out",
        "items": {
            "Interior Walls":     {"unit_cost": 8_000,  "qty": 1},
            "Electrical Work":    {"unit_cost": 12_000, "qty": 1},
            "Lighting":           {"unit_cost": 5_000,  "qty": 1},
            "Flooring":           {"unit_cost": 6_000,  "qty": 1},
            "Paint & Finishes":   {"unit_cost": 3_000,  "qty": 1},
            "Signage":            {"unit_cost": 6_000,  "qty": 1},
        },
    },
    "pos_system": {
        "label": "POS System & Technology",
        "items": {
            "Square Terminal":       {"unit_cost": 299, "qty": 1},
            "Backup Card Reader":    {"unit_cost": 49,  "qty": 1},
            "Cash Drawer":           {"unit_cost": 109, "qty": 1},
            "Receipt Printer":       {"unit_cost": 299, "qty": 1},
            "iPad & Stand":          {"unit_cost": 650, "qty": 1},
            "Barcode Scanner":       {"unit_cost": 150, "qty": 1},
            "Installation & Setup":  {"unit_cost": 444, "qty": 1},
            "Contingency Buffer":    {"unit_cost": 3_000, "qty": 1},
        },
    },
    "other": {
        "label": "Other Startup Costs",
        "items": {
            "Initial Inventory":           {"unit_cost": 10_000, "qty": 1},
            "Deposits & Working Capital":  {"unit_cost": 8_000,  "qty": 1},
            "Contingency & Pre-Opening":   {"unit_cost": 24_140, "qty": 1},
            "Reserved for Margin":         {"unit_cost": 27_800, "qty": 1},
        },
    },
}


# =============================================================================
# OPERATING EXPENSES — YEAR 1 BUDGET
# =============================================================================
# This is structured as a list of tuples: (name, category, amount)
# Category tells us how to classify it on the income statement.
#
# LEARNING NOTE: A "tuple" is like a list but immutable (can't change it).
# Written with parentheses () instead of brackets [].
# Good for data that shouldn't be modified after creation.

OPEX_BUDGET = [
    # (Line Item,                        Category,        Year 1 Amount)
    ("Merchant & Card Processing Fees",  "variable",      10_160),
    ("Rent and CAM",                     "fixed",         78_000),
    ("Utilities and Internet",           "fixed",         18_000),
    ("Insurance",                        "fixed",         12_000),
    ("Owner Salary",                     "fixed",         45_000),
    ("Part-Time Wages",                  "semi_variable", 65_700),
    ("Payroll Taxes and Benefits",       "semi_variable", 13_284),
    ("Tournament Prizes",               "fixed",         12_000),
    ("Software and IT Subscriptions",   "fixed",         12_000),
    ("Marketing and Advertising",        "fixed",          6_000),
    ("Repairs and Maintenance",          "fixed",          6_000),
    ("Janitorial and Trash",             "fixed",          7_200),
    ("Accounting and Professional Fees", "fixed",          3_600),
    ("Office and Miscellaneous",         "fixed",          3_600),
]
# NOTE: Depreciation and Interest are NOT in this list.
# They get calculated separately in the model engine because:
#   - Depreciation is a non-cash charge (affects IS but not cash flow directly)
#   - Interest depends on the loan balance (changes each year as you pay down principal)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
# These are small utility functions that make the data easier to work with.
# LEARNING NOTE: Functions are reusable blocks of code. Define once, call anywhere.

def calc_max_daily_device_hours() -> int:
    """
    Calculate the theoretical maximum device-hours per day.
    Returns: total_devices × operating_hours_per_day

    PYTHON CONCEPT: Type hints (-> int) tell the reader what the function returns.
    They don't enforce anything — they're documentation.
    """
    cap = ASSUMPTIONS["capacity"]
    return cap["total_devices"] * cap["operating_hours_per_day"]


def calc_utilization(daily_hours: int) -> float:
    """
    Convert daily device-hours to a utilization percentage.

    Example:
      calc_utilization(100)  →  0.2083  (20.8%)

    PYTHON CONCEPT: f-strings and formatting
      f"{calc_utilization(100):.1%}"  →  "20.8%"
    """
    max_hours = calc_max_daily_device_hours()
    return daily_hours / max_hours


def calc_gaming_revenue(daily_hours: int, price: float = None) -> float:
    """
    Calculate annual gaming revenue from daily device-hours and price.

    Formula: daily_hours × price_per_hour × 365

    PYTHON CONCEPT: Default arguments (price=None means "use the config value
    if the caller doesn't specify one"). This makes functions flexible.
    """
    if price is None:
        price = ASSUMPTIONS["pricing"]["price_per_hour"]
    return daily_hours * price * ASSUMPTIONS["capacity"]["days_per_year"]


def calc_startup_category_total(category_key: str) -> float:
    """
    Sum up all line items in a startup cost category.

    Example:
      calc_startup_category_total("gaming_pcs")  →  33360.0

    PYTHON CONCEPT: Dictionary comprehension / generator expression.
    The sum() with a generator is a Pythonic pattern you'll use constantly.
    """
    items = STARTUP_COSTS[category_key]["items"]
    return sum(v["unit_cost"] * v["qty"] for v in items.values())


def calc_total_startup_costs() -> float:
    """Sum ALL startup cost categories."""
    return sum(calc_startup_category_total(k) for k in STARTUP_COSTS)


def get_opex_total() -> float:
    """Sum Year 1 operating expenses (excluding depreciation and interest)."""
    return sum(amount for _, _, amount in OPEX_BUDGET)
    # PYTHON CONCEPT: Tuple unpacking with _ for values you don't need.
    # (name, category, amount) — we only need amount, so _ skips the rest.


# =============================================================================
# SELF-TEST: Run this file directly to verify the data
# =============================================================================
# PYTHON CONCEPT: __name__ == "__main__" only runs when you execute this file
# directly (python config.py), NOT when another file imports it.

if __name__ == "__main__":
    print("=" * 60)
    print("GAMING ARENA — CONFIG VALIDATION")
    print("=" * 60)

    max_hrs = calc_max_daily_device_hours()
    print(f"\nMax daily device-hours: {max_hrs}")
    print(f"Base case utilization:  {calc_utilization(100):.1%}")

    print(f"\nBase case gaming revenue: ${calc_gaming_revenue(100):,.0f}")
    print(f"F&B revenue:              ${ASSUMPTIONS['fnb']['year1_revenue']:,.0f}")
    total_rev = calc_gaming_revenue(100) + ASSUMPTIONS["fnb"]["year1_revenue"]
    print(f"Total Year 1 revenue:     ${total_rev:,.0f}")

    print(f"\nTotal startup costs:      ${calc_total_startup_costs():,.0f}")
    print(f"Total Year 1 OpEx:        ${get_opex_total():,.0f}")

    # Print each startup category
    print("\n--- Startup Cost Breakdown ---")
    for key, cat in STARTUP_COSTS.items():
        total = calc_startup_category_total(key)
        print(f"  {cat['label']:.<40s} ${total:>10,.0f}")
    print(f"  {'TOTAL':.<40s} ${calc_total_startup_costs():>10,.0f}")

    print("\n--- OpEx Budget ---")
    for name, category, amount in OPEX_BUDGET:
        print(f"  [{category:.<14s}] {name:.<36s} ${amount:>10,.0f}")
    print(f"  {'TOTAL':.<52s} ${get_opex_total():>10,.0f}")
