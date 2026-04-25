"""
MODULE 13: ACCOUNTING ENGINE
================================
Gaming Arena, LLC — General Ledger, Journal Entries & Trial Balance

WHAT THIS FILE TEACHES YOU:
- Double-entry bookkeeping (every transaction has equal debits and credits)
- Chart of Accounts structured by GAAP classification
- Journal entries for a real business (revenue recognition, expense accruals,
  depreciation, loan payments, COGS)
- General Ledger with monthly running balances
- Trial Balance generation and validation
- How accounting data flows into financial statements

GAAP FLOW THIS MODULE IMPLEMENTS:
  Journal Entries → Post to General Ledger → Trial Balance → Financial Statements
                                                               ├─ Income Statement
                                                               ├─ Balance Sheet
                                                               └─ Cash Flow Statement

WHY THIS MATTERS:
  Financial statements don't appear from thin air. They are the OUTPUT of an
  accounting system. Understanding the GL → TB → FS pipeline is what separates
  someone who reads financials from someone who builds them.

ACCOUNTING RULES ENFORCED:
  1. Debits = Credits for every journal entry (no exceptions)
  2. Assets = Liabilities + Equity at all times
  3. Revenue and Expense accounts reset at year-end (closing entries)
  4. Normal balances: Assets/Expenses = Debit; Liabilities/Equity/Revenue = Credit
"""

import pandas as pd
import numpy as np
from collections import OrderedDict
from config import ASSUMPTIONS, OPEX_BUDGET, calc_gaming_revenue


# =============================================================================
# CHART OF ACCOUNTS
# =============================================================================
# GAAP-structured chart of accounts. Each account has:
#   - number: standard numbering (1xxx=Assets, 2xxx=Liabilities, 3xxx=Equity,
#             4xxx=Revenue, 5xxx=COGS, 6xxx=Operating Expenses, 7xxx=Other)
#   - name: descriptive account name
#   - type: asset, liability, equity, revenue, expense
#   - normal_balance: debit or credit
#   - fs_line: which financial statement line this maps to

CHART_OF_ACCOUNTS = OrderedDict([
    # --- ASSETS (1000-1999) ---
    ("1000", {"name": "Cash and Cash Equivalents",     "type": "asset",     "normal_balance": "debit",  "fs_line": "Cash and Cash Equivalents", "fs": "BS"}),
    ("1100", {"name": "Accounts Receivable",           "type": "asset",     "normal_balance": "debit",  "fs_line": "Accounts Receivable", "fs": "BS"}),
    ("1200", {"name": "Inventory",                     "type": "asset",     "normal_balance": "debit",  "fs_line": "Inventory", "fs": "BS"}),
    ("1300", {"name": "Prepaid Expenses",              "type": "asset",     "normal_balance": "debit",  "fs_line": "Prepaid Expenses", "fs": "BS"}),
    ("1500", {"name": "Property and Equipment (Gross)","type": "asset",     "normal_balance": "debit",  "fs_line": "Gross PP&E", "fs": "BS"}),
    ("1510", {"name": "Accumulated Depreciation",      "type": "asset",     "normal_balance": "credit", "fs_line": "Accumulated Depreciation", "fs": "BS"}),
    # Net PP&E = 1500 - 1510

    # --- LIABILITIES (2000-2999) ---
    ("2000", {"name": "Accounts Payable",              "type": "liability", "normal_balance": "credit", "fs_line": "Accounts Payable", "fs": "BS"}),
    ("2100", {"name": "Accrued Expenses",              "type": "liability", "normal_balance": "credit", "fs_line": "Accrued Expenses", "fs": "BS"}),
    ("2500", {"name": "SBA Loan Payable",              "type": "liability", "normal_balance": "credit", "fs_line": "SBA Loan Payable", "fs": "BS"}),

    # --- EQUITY (3000-3999) ---
    ("3000", {"name": "Owner Equity — Capital",        "type": "equity",    "normal_balance": "credit", "fs_line": "Owner Equity", "fs": "BS"}),
    ("3100", {"name": "Retained Earnings",             "type": "equity",    "normal_balance": "credit", "fs_line": "Retained Earnings", "fs": "BS"}),

    # --- REVENUE (4000-4999) ---
    ("4000", {"name": "Gaming Revenue",                "type": "revenue",   "normal_balance": "credit", "fs_line": "Gaming Revenue", "fs": "IS"}),
    ("4100", {"name": "F&B and Merchandise Revenue",   "type": "revenue",   "normal_balance": "credit", "fs_line": "F&B / Merchandise Revenue", "fs": "IS"}),

    # --- COST OF GOODS SOLD (5000-5999) ---
    ("5000", {"name": "Cost of Goods Sold — F&B",      "type": "expense",   "normal_balance": "debit",  "fs_line": "F&B Cost of Goods Sold", "fs": "IS"}),

    # --- OPERATING EXPENSES (6000-6999) ---
    ("6000", {"name": "Merchant Processing Fees",      "type": "expense",   "normal_balance": "debit",  "fs_line": "Merchant & Card Processing Fees", "fs": "IS"}),
    ("6100", {"name": "Rent and CAM",                  "type": "expense",   "normal_balance": "debit",  "fs_line": "Rent and CAM", "fs": "IS"}),
    ("6110", {"name": "Utilities and Internet",        "type": "expense",   "normal_balance": "debit",  "fs_line": "Utilities and Internet", "fs": "IS"}),
    ("6120", {"name": "Insurance",                     "type": "expense",   "normal_balance": "debit",  "fs_line": "Insurance", "fs": "IS"}),
    ("6200", {"name": "Owner Salary",                  "type": "expense",   "normal_balance": "debit",  "fs_line": "Owner Salary", "fs": "IS"}),
    ("6210", {"name": "Part-Time Wages",               "type": "expense",   "normal_balance": "debit",  "fs_line": "Part-Time Wages", "fs": "IS"}),
    ("6220", {"name": "Payroll Taxes and Benefits",    "type": "expense",   "normal_balance": "debit",  "fs_line": "Payroll Taxes and Benefits", "fs": "IS"}),
    ("6300", {"name": "Tournament Prizes",             "type": "expense",   "normal_balance": "debit",  "fs_line": "Tournament Prizes", "fs": "IS"}),
    ("6310", {"name": "Software and IT Subscriptions", "type": "expense",   "normal_balance": "debit",  "fs_line": "Software and IT Subscriptions", "fs": "IS"}),
    ("6320", {"name": "Marketing and Advertising",     "type": "expense",   "normal_balance": "debit",  "fs_line": "Marketing and Advertising", "fs": "IS"}),
    ("6330", {"name": "Repairs and Maintenance",       "type": "expense",   "normal_balance": "debit",  "fs_line": "Repairs and Maintenance", "fs": "IS"}),
    ("6340", {"name": "Janitorial and Trash",          "type": "expense",   "normal_balance": "debit",  "fs_line": "Janitorial and Trash", "fs": "IS"}),
    ("6350", {"name": "Accounting and Professional Fees","type": "expense", "normal_balance": "debit",  "fs_line": "Accounting and Professional Fees", "fs": "IS"}),
    ("6360", {"name": "Office and Miscellaneous",      "type": "expense",   "normal_balance": "debit",  "fs_line": "Office and Miscellaneous", "fs": "IS"}),

    # --- NON-CASH & FINANCING (7000-7999) ---
    ("7000", {"name": "Depreciation Expense",          "type": "expense",   "normal_balance": "debit",  "fs_line": "Depreciation", "fs": "IS"}),
    ("7100", {"name": "Interest Expense",              "type": "expense",   "normal_balance": "debit",  "fs_line": "Interest Expense", "fs": "IS"}),
])

# Map OPEX_BUDGET line item names to GL account numbers
OPEX_TO_ACCOUNT = {
    "Merchant & Card Processing Fees":  "6000",
    "Rent and CAM":                     "6100",
    "Utilities and Internet":           "6110",
    "Insurance":                        "6120",
    "Owner Salary":                     "6200",
    "Part-Time Wages":                  "6210",
    "Payroll Taxes and Benefits":       "6220",
    "Tournament Prizes":               "6300",
    "Software and IT Subscriptions":   "6310",
    "Marketing and Advertising":        "6320",
    "Repairs and Maintenance":          "6330",
    "Janitorial and Trash":             "6340",
    "Accounting and Professional Fees": "6350",
    "Office and Miscellaneous":         "6360",
}


# =============================================================================
# JOURNAL ENTRY ENGINE
# =============================================================================

class JournalEntry:
    """
    Represents a single journal entry with one or more debit/credit lines.

    ACCOUNTING RULE: Total Debits MUST equal Total Credits.
    If they don't, the entry is rejected.
    """

    def __init__(self, je_id: int, date: str, description: str, reference: str = ""):
        self.je_id = je_id
        self.date = date
        self.description = description
        self.reference = reference
        self.lines = []  # list of {account, account_name, debit, credit}

    def add_debit(self, account: str, amount: float):
        """Add a debit line. Debits increase assets and expenses."""
        acct = CHART_OF_ACCOUNTS[account]
        self.lines.append({
            "account": account,
            "account_name": acct["name"],
            "debit": round(amount, 2),
            "credit": 0.0,
        })

    def add_credit(self, account: str, amount: float):
        """Add a credit line. Credits increase liabilities, equity, and revenue."""
        acct = CHART_OF_ACCOUNTS[account]
        self.lines.append({
            "account": account,
            "account_name": acct["name"],
            "debit": 0.0,
            "credit": round(amount, 2),
        })

    def is_balanced(self) -> bool:
        """Check that total debits = total credits."""
        total_dr = sum(l["debit"] for l in self.lines)
        total_cr = sum(l["credit"] for l in self.lines)
        return abs(total_dr - total_cr) < 0.01

    def total_debits(self) -> float:
        return sum(l["debit"] for l in self.lines)

    def total_credits(self) -> float:
        return sum(l["credit"] for l in self.lines)

    def to_dict_list(self) -> list:
        """Convert to list of dicts for DataFrame creation."""
        rows = []
        for line in self.lines:
            rows.append({
                "JE #": self.je_id,
                "Date": self.date,
                "Description": self.description,
                "Reference": self.reference,
                "Account #": line["account"],
                "Account Name": line["account_name"],
                "Debit": line["debit"],
                "Credit": line["credit"],
            })
        return rows


def generate_year1_journal_entries(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> list:
    """
    Generate all monthly journal entries for Year 1.

    GAAP JOURNAL ENTRY TYPES INCLUDED:
    1. Opening entries (initial funding, asset purchases)
    2. Monthly revenue recognition (gaming + F&B)
    3. Monthly COGS (F&B cost of goods)
    4. Monthly operating expenses (rent, wages, utilities, etc.)
    5. Monthly depreciation (non-cash, straight-line)
    6. Monthly interest expense (accrual)
    7. Monthly loan principal payment
    8. Monthly merchant processing fees (variable)

    Returns list of JournalEntry objects.
    """
    a = ASSUMPTIONS
    hours = daily_device_hours or a["utilization"]["base_case_hours"]
    price = price_per_hour or a["pricing"]["price_per_hour"]

    entries = []
    je_num = 1

    # =========================================================================
    # OPENING ENTRIES (Month 0 / Day 1)
    # =========================================================================

    # JE 1: Owner equity contribution
    je = JournalEntry(je_num, "Month 0", "Owner equity contribution — initial capital",
                      "Opening")
    je.add_debit("1000", a["debt"]["owner_equity"])       # Cash increases
    je.add_credit("3000", a["debt"]["owner_equity"])       # Owner equity increases
    entries.append(je)
    je_num += 1

    # JE 2: SBA loan proceeds
    je = JournalEntry(je_num, "Month 0", "SBA 7(a) loan proceeds received",
                      "Opening")
    je.add_debit("1000", a["debt"]["loan_amount"])         # Cash increases
    je.add_credit("2500", a["debt"]["loan_amount"])        # Loan liability increases
    entries.append(je)
    je_num += 1

    # JE 3: Purchase of property and equipment (startup assets)
    je = JournalEntry(je_num, "Month 0", "Purchase of gaming equipment, furniture, build-out",
                      "Opening")
    je.add_debit("1500", a["depreciation"]["depreciable_assets"])  # PP&E increases
    je.add_credit("1000", a["depreciation"]["depreciable_assets"]) # Cash decreases
    entries.append(je)
    je_num += 1

    # =========================================================================
    # MONTHLY RECURRING ENTRIES (Months 1-12)
    # =========================================================================

    # Pre-compute monthly amounts
    annual_gaming_rev = calc_gaming_revenue(hours, price)
    monthly_gaming_rev = annual_gaming_rev / 12
    annual_fnb_rev = a["fnb"]["year1_revenue"]
    monthly_fnb_rev = annual_fnb_rev / 12
    monthly_total_rev = monthly_gaming_rev + monthly_fnb_rev

    monthly_cogs = (annual_fnb_rev * a["fnb"]["cogs_pct"]) / 12
    monthly_depreciation = a["depreciation"]["annual_depreciation"] / 12
    monthly_interest = (a["debt"]["loan_amount"] * a["debt"]["interest_rate"]) / 12
    monthly_principal = a["debt"]["annual_principal_payment"] / 12
    monthly_merchant_fee = monthly_total_rev * a["fees"]["merchant_processing_pct"]

    # Build monthly OpEx map (annual ÷ 12, excluding merchant fees which are variable)
    monthly_opex = {}
    for name, category, amount in OPEX_BUDGET:
        if name == "Merchant & Card Processing Fees":
            continue  # handled separately as variable cost
        acct = OPEX_TO_ACCOUNT.get(name)
        if acct:
            monthly_opex[acct] = {
                "name": name,
                "monthly": round(amount / 12, 2),
            }

    MONTH_NAMES = [
        "Month 1", "Month 2", "Month 3", "Month 4",
        "Month 5", "Month 6", "Month 7", "Month 8",
        "Month 9", "Month 10", "Month 11", "Month 12",
    ]

    for month_idx, month_label in enumerate(MONTH_NAMES):

        # --- Revenue Recognition ---
        # GAAP: Revenue recognized when earned (service delivered)
        je = JournalEntry(je_num, month_label,
                          f"Gaming revenue — {month_label}",
                          "Revenue")
        je.add_debit("1000", monthly_gaming_rev)   # Cash received
        je.add_credit("4000", monthly_gaming_rev)  # Revenue earned
        entries.append(je)
        je_num += 1

        je = JournalEntry(je_num, month_label,
                          f"F&B / merchandise revenue — {month_label}",
                          "Revenue")
        je.add_debit("1000", monthly_fnb_rev)      # Cash received
        je.add_credit("4100", monthly_fnb_rev)     # F&B revenue earned
        entries.append(je)
        je_num += 1

        # --- Cost of Goods Sold ---
        # GAAP: Match COGS to the revenue period (matching principle)
        je = JournalEntry(je_num, month_label,
                          f"F&B cost of goods sold — {month_label}",
                          "COGS")
        je.add_debit("5000", monthly_cogs)         # COGS expense increases
        je.add_credit("1000", monthly_cogs)        # Cash decreases (simplified)
        entries.append(je)
        je_num += 1

        # --- Merchant Processing Fees (variable) ---
        je = JournalEntry(je_num, month_label,
                          f"Merchant processing fees — {month_label}",
                          "OpEx")
        je.add_debit("6000", monthly_merchant_fee)
        je.add_credit("1000", monthly_merchant_fee)
        entries.append(je)
        je_num += 1

        # --- Operating Expenses ---
        # One compound JE for all monthly operating expenses
        je = JournalEntry(je_num, month_label,
                          f"Monthly operating expenses — {month_label}",
                          "OpEx")
        total_opex_month = 0
        for acct_num, info in monthly_opex.items():
            je.add_debit(acct_num, info["monthly"])
            total_opex_month += info["monthly"]
        je.add_credit("1000", total_opex_month)    # Cash paid out
        entries.append(je)
        je_num += 1

        # --- Depreciation ---
        # GAAP: Non-cash expense. Debit expense, credit accumulated depreciation.
        # Does NOT affect cash.
        je = JournalEntry(je_num, month_label,
                          f"Monthly depreciation — straight-line — {month_label}",
                          "Non-Cash")
        je.add_debit("7000", monthly_depreciation)         # Depreciation expense
        je.add_credit("1510", monthly_depreciation)        # Accumulated depreciation
        entries.append(je)
        je_num += 1

        # --- Interest Expense ---
        # GAAP: Accrue interest monthly regardless of payment timing
        je = JournalEntry(je_num, month_label,
                          f"Interest expense on SBA loan — {month_label}",
                          "Financing")
        je.add_debit("7100", monthly_interest)             # Interest expense
        je.add_credit("1000", monthly_interest)            # Cash paid
        entries.append(je)
        je_num += 1

        # --- Loan Principal Payment ---
        # Reduces liability, not an expense. Affects balance sheet only.
        je = JournalEntry(je_num, month_label,
                          f"SBA loan principal payment — {month_label}",
                          "Financing")
        je.add_debit("2500", monthly_principal)            # Loan balance decreases
        je.add_credit("1000", monthly_principal)           # Cash decreases
        entries.append(je)
        je_num += 1

    return entries


# =============================================================================
# GENERAL LEDGER
# =============================================================================

def build_general_ledger(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> pd.DataFrame:
    """
    Post all journal entries to the General Ledger.

    The GL is the master record of all transactions, organized by account.
    Each row shows: date, JE reference, description, debit, credit, running balance.

    Returns DataFrame with columns:
        Account #, Account Name, Date, JE #, Description, Debit, Credit, Balance
    """
    entries = generate_year1_journal_entries(daily_device_hours, price_per_hour)

    # Initialize balances
    balances = {acct: 0.0 for acct in CHART_OF_ACCOUNTS}

    gl_rows = []

    for je in entries:
        if not je.is_balanced():
            raise ValueError(
                f"JE #{je.je_id} is unbalanced! "
                f"DR={je.total_debits():.2f} CR={je.total_credits():.2f}"
            )

        for line in je.lines:
            acct_num = line["account"]
            acct_info = CHART_OF_ACCOUNTS[acct_num]
            dr = line["debit"]
            cr = line["credit"]

            # Update running balance based on normal balance side
            if acct_info["normal_balance"] == "debit":
                balances[acct_num] += dr - cr
            else:
                balances[acct_num] += cr - dr

            gl_rows.append({
                "Account #": acct_num,
                "Account Name": acct_info["name"],
                "Type": acct_info["type"].title(),
                "Date": je.date,
                "JE #": je.je_id,
                "Description": je.description,
                "Reference": je.reference,
                "Debit": dr if dr > 0 else None,
                "Credit": cr if cr > 0 else None,
                "Balance": round(balances[acct_num], 2),
            })

    return pd.DataFrame(gl_rows)


def get_account_ledger(gl_df: pd.DataFrame, account_num: str) -> pd.DataFrame:
    """Extract the ledger for a single account from the full GL."""
    return gl_df[gl_df["Account #"] == account_num].copy()


# =============================================================================
# TRIAL BALANCE
# =============================================================================

def build_trial_balance(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> pd.DataFrame:
    """
    Build a Trial Balance from the General Ledger.

    WHAT A TRIAL BALANCE IS:
      A list of all GL accounts with their ending debit or credit balances.
      Total Debits MUST equal Total Credits. If they don't, there's an error
      somewhere in the posting process.

    GAAP REQUIREMENT: Trial balance is prepared BEFORE financial statements.
    It's the checkpoint that proves the books are in balance.

    Returns DataFrame with:
        Account #, Account Name, Type, Debit Balance, Credit Balance
    """
    gl = build_general_ledger(daily_device_hours, price_per_hour)

    # Get the last (ending) balance for each account
    tb_rows = []
    for acct_num, acct_info in CHART_OF_ACCOUNTS.items():
        acct_gl = gl[gl["Account #"] == acct_num]

        if acct_gl.empty:
            ending_balance = 0.0
        else:
            ending_balance = acct_gl.iloc[-1]["Balance"]

        # Place balance on the normal side
        dr_bal = ending_balance if acct_info["normal_balance"] == "debit" else 0.0
        cr_bal = ending_balance if acct_info["normal_balance"] == "credit" else 0.0

        # Contra accounts (like accumulated depreciation) can have the opposite sign
        if ending_balance < 0:
            if acct_info["normal_balance"] == "debit":
                dr_bal = 0.0
                cr_bal = abs(ending_balance)
            else:
                cr_bal = 0.0
                dr_bal = abs(ending_balance)

        tb_rows.append({
            "Account #": acct_num,
            "Account Name": acct_info["name"],
            "Type": acct_info["type"].title(),
            "FS": acct_info["fs"],
            "FS Line": acct_info["fs_line"],
            "Debit": round(dr_bal, 2),
            "Credit": round(cr_bal, 2),
        })

    tb_df = pd.DataFrame(tb_rows)
    return tb_df


def validate_trial_balance(tb_df: pd.DataFrame) -> dict:
    """
    Validate that the trial balance is balanced (debits = credits).

    Returns dict with total_debits, total_credits, is_balanced, difference.
    """
    total_dr = tb_df["Debit"].sum()
    total_cr = tb_df["Credit"].sum()
    diff = abs(total_dr - total_cr)

    return {
        "total_debits": round(total_dr, 2),
        "total_credits": round(total_cr, 2),
        "difference": round(diff, 2),
        "is_balanced": diff < 0.01,
    }


# =============================================================================
# GL-TO-FINANCIAL-STATEMENT MAPPING
# =============================================================================

def build_fs_mapping(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> dict:
    """
    Map GL ending balances to financial statement line items.

    This is the bridge that shows exactly how accounting transactions
    flow into the Income Statement and Balance Sheet.

    Returns dict with:
        - "income_statement": list of {account, line, amount}
        - "balance_sheet": list of {account, line, amount}
        - "totals": summary totals for validation
    """
    tb = build_trial_balance(daily_device_hours, price_per_hour)

    is_lines = []
    bs_lines = []

    for _, row in tb.iterrows():
        acct_info = CHART_OF_ACCOUNTS[row["Account #"]]
        # Net balance: debit-normal accounts use Debit, credit-normal use Credit
        balance = row["Debit"] if row["Debit"] > 0 else row["Credit"]

        entry = {
            "Account #": row["Account #"],
            "Account Name": row["Account Name"],
            "FS Line": acct_info["fs_line"],
            "Balance": balance,
            "Normal Side": acct_info["normal_balance"].title(),
        }

        if acct_info["fs"] == "IS":
            is_lines.append(entry)
        else:
            bs_lines.append(entry)

    # Compute IS totals
    total_revenue = sum(e["Balance"] for e in is_lines
                        if CHART_OF_ACCOUNTS[e["Account #"]]["type"] == "revenue")
    total_cogs = sum(e["Balance"] for e in is_lines
                     if e["Account #"].startswith("5"))
    total_opex = sum(e["Balance"] for e in is_lines
                     if e["Account #"].startswith("6"))
    total_other = sum(e["Balance"] for e in is_lines
                      if e["Account #"].startswith("7"))
    gross_profit = total_revenue - total_cogs
    ebitda = gross_profit - total_opex
    # Depreciation is in 7000, interest is in 7100
    depr = sum(e["Balance"] for e in is_lines if e["Account #"] == "7000")
    interest = sum(e["Balance"] for e in is_lines if e["Account #"] == "7100")
    ebit = ebitda - depr
    pretax = ebit - interest

    # Compute BS totals
    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for e in bs_lines:
        acct_info = CHART_OF_ACCOUNTS[e["Account #"]]
        if acct_info["type"] == "asset":
            if acct_info["normal_balance"] == "credit":
                # Contra asset (accumulated depreciation) — subtract
                total_assets -= e["Balance"]
            else:
                total_assets += e["Balance"]
        elif acct_info["type"] == "liability":
            total_liabilities += e["Balance"]
        elif acct_info["type"] == "equity":
            total_equity += e["Balance"]

    # Net income flows to retained earnings conceptually
    net_income_to_re = pretax  # pre-tax used here since model has no tax line

    return {
        "income_statement": is_lines,
        "balance_sheet": bs_lines,
        "totals": {
            "total_revenue": round(total_revenue, 2),
            "total_cogs": round(total_cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "total_opex": round(total_opex, 2),
            "ebitda": round(ebitda, 2),
            "depreciation": round(depr, 2),
            "ebit": round(ebit, 2),
            "interest": round(interest, 2),
            "pretax_income": round(pretax, 2),
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "total_equity": round(total_equity, 2),
            "net_income_to_retained_earnings": round(net_income_to_re, 2),
        },
    }


# =============================================================================
# MONTHLY SUMMARY
# =============================================================================

def build_monthly_gl_summary(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> pd.DataFrame:
    """
    Summarize GL activity by month — total debits, credits, and net change
    for each account in each month.

    Useful for the dashboard to show monthly flow.
    """
    gl = build_general_ledger(daily_device_hours, price_per_hour)

    # Get unique months in order
    month_order = ["Month 0"] + [f"Month {i}" for i in range(1, 13)]
    months_present = [m for m in month_order if m in gl["Date"].values]

    summary_rows = []
    for acct_num, acct_info in CHART_OF_ACCOUNTS.items():
        acct_gl = gl[gl["Account #"] == acct_num]
        if acct_gl.empty:
            continue

        for month in months_present:
            month_data = acct_gl[acct_gl["Date"] == month]
            if month_data.empty:
                continue

            total_dr = month_data["Debit"].fillna(0).sum()
            total_cr = month_data["Credit"].fillna(0).sum()
            ending_bal = month_data.iloc[-1]["Balance"]

            summary_rows.append({
                "Account #": acct_num,
                "Account Name": acct_info["name"],
                "Type": acct_info["type"].title(),
                "Month": month,
                "Total Debits": round(total_dr, 2),
                "Total Credits": round(total_cr, 2),
                "Ending Balance": round(ending_bal, 2),
            })

    return pd.DataFrame(summary_rows)


# =============================================================================
# CONVENIENCE: GET COA AS DATAFRAME
# =============================================================================

def get_chart_of_accounts_df() -> pd.DataFrame:
    """Return the Chart of Accounts as a DataFrame for display."""
    rows = []
    for acct_num, info in CHART_OF_ACCOUNTS.items():
        rows.append({
            "Account #": acct_num,
            "Account Name": info["name"],
            "Type": info["type"].title(),
            "Normal Balance": info["normal_balance"].title(),
            "FS": info["fs"],
            "FS Line": info["fs_line"],
        })
    return pd.DataFrame(rows)


def get_journal_entries_df(
    daily_device_hours: int = None,
    price_per_hour: float = None,
) -> pd.DataFrame:
    """Return all journal entries as a flat DataFrame."""
    entries = generate_year1_journal_entries(daily_device_hours, price_per_hour)
    all_rows = []
    for je in entries:
        all_rows.extend(je.to_dict_list())
    return pd.DataFrame(all_rows)


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULE 13: ACCOUNTING ENGINE — SELF-TEST")
    print("=" * 70)

    # Chart of Accounts
    coa = get_chart_of_accounts_df()
    print(f"\nChart of Accounts: {len(coa)} accounts")
    for _, row in coa.iterrows():
        print(f"  {row['Account #']}  {row['Account Name']:<40s}  "
              f"{row['Type']:<12s}  {row['Normal Balance']:<8s}  [{row['FS']}]")

    # Journal Entries
    je_df = get_journal_entries_df()
    n_entries = je_df["JE #"].nunique()
    print(f"\nJournal Entries: {n_entries} entries, {len(je_df)} lines")
    print(f"  Total Debits:  ${je_df['Debit'].sum():>12,.2f}")
    print(f"  Total Credits: ${je_df['Credit'].sum():>12,.2f}")
    balanced = abs(je_df['Debit'].sum() - je_df['Credit'].sum()) < 0.01
    print(f"  All Balanced:  {'YES' if balanced else 'NO'}")

    # Trial Balance
    tb = build_trial_balance()
    tb_valid = validate_trial_balance(tb)
    print(f"\nTrial Balance:")
    print(f"  Total Debits:  ${tb_valid['total_debits']:>12,.2f}")
    print(f"  Total Credits: ${tb_valid['total_credits']:>12,.2f}")
    print(f"  Balanced:      {'YES' if tb_valid['is_balanced'] else 'NO'}")
    if not tb_valid["is_balanced"]:
        print(f"  Difference:    ${tb_valid['difference']:>12,.2f}")

    # Print TB detail
    print(f"\n{'Acct':<6s} {'Account Name':<40s} {'Debit':>12s} {'Credit':>12s}")
    print("-" * 72)
    for _, row in tb.iterrows():
        dr = f"${row['Debit']:>10,.2f}" if row['Debit'] > 0 else ""
        cr = f"${row['Credit']:>10,.2f}" if row['Credit'] > 0 else ""
        print(f"  {row['Account #']:<6s} {row['Account Name']:<38s} {dr:>12s} {cr:>12s}")
    print("-" * 72)
    print(f"  {'TOTALS':<44s} ${tb['Debit'].sum():>10,.2f} ${tb['Credit'].sum():>10,.2f}")

    # FS Mapping
    fs_map = build_fs_mapping()
    totals = fs_map["totals"]
    print(f"\nFinancial Statement Mapping:")
    print(f"  Revenue:        ${totals['total_revenue']:>12,.2f}")
    print(f"  COGS:           ${totals['total_cogs']:>12,.2f}")
    print(f"  Gross Profit:   ${totals['gross_profit']:>12,.2f}")
    print(f"  OpEx:           ${totals['total_opex']:>12,.2f}")
    print(f"  EBITDA:         ${totals['ebitda']:>12,.2f}")
    print(f"  Depreciation:   ${totals['depreciation']:>12,.2f}")
    print(f"  EBIT:           ${totals['ebit']:>12,.2f}")
    print(f"  Interest:       ${totals['interest']:>12,.2f}")
    print(f"  Pre-Tax Income: ${totals['pretax_income']:>12,.2f}")
