"""Mock data simulating GraphQL API responses.

These mock tools represent what the MCP server would return.
In production, these would call the real GraphQL API via the MCP server.
"""

# --- Mock business database ---
BUSINESSES = {
    "BIZ001": {
        "business_id": "BIZ001",
        "business_name": "Maple Leaf Consulting Inc.",
        "accounting_method": "accrual",
        "jurisdiction": "ON",
        "fiscal_year_end": "2024-12-31",
        "business_type": "sole_proprietorship",
    },
    "BIZ002": {
        "business_id": "BIZ002",
        "business_name": "Pacific Coast Design Studio",
        "accounting_method": "cash",
        "jurisdiction": "BC",
        "fiscal_year_end": "2024-12-31",
        "business_type": "sole_proprietorship",
    },
    "BIZ003": {
        "business_id": "BIZ003",
        "business_name": "Prairie Tech Solutions",
        "accounting_method": "accrual",
        "jurisdiction": "AB",
        "fiscal_year_end": "2024-12-31",
        "business_type": "partnership",
    },
}

# --- Mock income data ---
INCOME_DATA = {
    "BIZ001": {
        "accounts": [
            {"name": "Consulting Revenue", "type": "CREDIT", "amount": 185000.00},
            {"name": "Workshop Revenue", "type": "CREDIT", "amount": 32000.00},
        ],
        "total_revenue": 217000.00,
    },
    "BIZ002": {
        "accounts": [
            {"name": "Design Services", "type": "CREDIT", "amount": 95000.00},
            {"name": "Licensing Revenue", "type": "CREDIT", "amount": 12000.00},
        ],
        "total_revenue": 107000.00,
    },
    "BIZ003": {
        "accounts": [
            {"name": "IT Consulting", "type": "CREDIT", "amount": 340000.00},
            {"name": "Support Contracts", "type": "CREDIT", "amount": 48000.00},
        ],
        "total_revenue": 388000.00,
    },
}

# --- Mock expense data ---
EXPENSE_DATA = {
    "BIZ001": {
        "accounts": [
            {"name": "Office Rent", "type": "DEBIT", "amount": 24000.00},
            {"name": "Software Subscriptions", "type": "DEBIT", "amount": 4800.00},
            {"name": "Professional Development", "type": "DEBIT", "amount": 3200.00},
            {"name": "Travel", "type": "DEBIT", "amount": 8500.00},
            {"name": "Insurance", "type": "DEBIT", "amount": 2400.00},
        ],
        "total_expenses": 42900.00,
    },
    "BIZ002": {
        "accounts": [
            {"name": "Home Office", "type": "DEBIT", "amount": 6000.00},
            {"name": "Adobe Creative Suite", "type": "DEBIT", "amount": 1200.00},
            {"name": "Equipment", "type": "DEBIT", "amount": 5500.00},
            {"name": "Marketing", "type": "DEBIT", "amount": 3000.00},
        ],
        "total_expenses": 15700.00,
    },
    "BIZ003": {
        "accounts": [
            {"name": "Office Lease", "type": "DEBIT", "amount": 48000.00},
            {"name": "Salaries", "type": "DEBIT", "amount": 120000.00},
            {"name": "Cloud Infrastructure", "type": "DEBIT", "amount": 18000.00},
            {"name": "Professional Services", "type": "DEBIT", "amount": 12000.00},
        ],
        "total_expenses": 198000.00,
    },
}

# --- Mock asset (HST/GST) data ---
ASSET_DATA = {
    "BIZ001": {
        "hst_collected": 28210.00,
        "hst_paid": 5577.00,
        "net_hst": 22633.00,
        "province": "ON",
        "hst_rate": 0.13,
    },
    "BIZ002": {
        "hst_collected": 5350.00,
        "hst_paid": 785.00,
        "net_hst": 4565.00,
        "province": "BC",
        "hst_rate": 0.05,
    },
    "BIZ003": {
        "hst_collected": 19400.00,
        "hst_paid": 9900.00,
        "net_hst": 9500.00,
        "province": "AB",
        "hst_rate": 0.05,
    },
}
