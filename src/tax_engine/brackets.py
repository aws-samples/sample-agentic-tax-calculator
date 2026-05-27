"""2024 CRA federal and provincial/territorial tax bracket data.

All bracket thresholds and rates are sourced from the Canada Revenue Agency
for the 2024 tax year. Basic personal amounts are the non-refundable tax
credits that effectively make the first portion of income tax-free.

Sources:
- Federal brackets: CRA T1 General 2024
- Provincial brackets: respective provincial tax acts, indexed for 2024
- Basic personal amounts: CRA and provincial tax credit schedules
"""

from src.tax_engine.interface import TaxBracket


# ---------------------------------------------------------------------------
# Supported jurisdictions - all 13 Canadian provinces and territories
# ---------------------------------------------------------------------------

SUPPORTED_JURISDICTIONS = [
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT",
]


# ---------------------------------------------------------------------------
# 2024 Federal tax brackets
# ---------------------------------------------------------------------------

FEDERAL_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=55867,  rate=0.15),
    TaxBracket(min_income=55867,  max_income=111733, rate=0.205),
    TaxBracket(min_income=111733, max_income=154906, rate=0.26),
    TaxBracket(min_income=154906, max_income=220000, rate=0.29),
    TaxBracket(min_income=220000, max_income=None,   rate=0.33),
]

FEDERAL_BASIC_PERSONAL_AMOUNT_2024 = 15705.0


# ---------------------------------------------------------------------------
# 2024 Provincial / territorial tax brackets
# ---------------------------------------------------------------------------

# Alberta
AB_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=148269, rate=0.10),
    TaxBracket(min_income=148269, max_income=177922, rate=0.12),
    TaxBracket(min_income=177922, max_income=237230, rate=0.13),
    TaxBracket(min_income=237230, max_income=355845, rate=0.14),
    TaxBracket(min_income=355845, max_income=None,   rate=0.15),
]

# British Columbia
BC_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=47937,  rate=0.0506),
    TaxBracket(min_income=47937,  max_income=95875,  rate=0.077),
    TaxBracket(min_income=95875,  max_income=110076, rate=0.105),
    TaxBracket(min_income=110076, max_income=133664, rate=0.1229),
    TaxBracket(min_income=133664, max_income=181232, rate=0.147),
    TaxBracket(min_income=181232, max_income=252752, rate=0.168),
    TaxBracket(min_income=252752, max_income=None,   rate=0.205),
]

# Manitoba
MB_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=47000,  rate=0.108),
    TaxBracket(min_income=47000,  max_income=100000, rate=0.1275),
    TaxBracket(min_income=100000, max_income=None,   rate=0.174),
]

# New Brunswick
NB_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=49958,  rate=0.094),
    TaxBracket(min_income=49958,  max_income=99916,  rate=0.14),
    TaxBracket(min_income=99916,  max_income=185064, rate=0.16),
    TaxBracket(min_income=185064, max_income=None,   rate=0.195),
]

# Newfoundland and Labrador
NL_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=43198,   rate=0.087),
    TaxBracket(min_income=43198,  max_income=86395,   rate=0.145),
    TaxBracket(min_income=86395,  max_income=154244,  rate=0.158),
    TaxBracket(min_income=154244, max_income=215943,  rate=0.178),
    TaxBracket(min_income=215943, max_income=275870,  rate=0.198),
    TaxBracket(min_income=275870, max_income=551739,  rate=0.208),
    TaxBracket(min_income=551739, max_income=1103478, rate=0.213),
    TaxBracket(min_income=1103478, max_income=None,   rate=0.218),
]

# Nova Scotia
NS_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=29590,  rate=0.0879),
    TaxBracket(min_income=29590,  max_income=59180,  rate=0.1495),
    TaxBracket(min_income=59180,  max_income=93000,  rate=0.1667),
    TaxBracket(min_income=93000,  max_income=150000, rate=0.175),
    TaxBracket(min_income=150000, max_income=None,   rate=0.21),
]

# Northwest Territories
NT_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=50597,  rate=0.059),
    TaxBracket(min_income=50597,  max_income=101198, rate=0.086),
    TaxBracket(min_income=101198, max_income=164525, rate=0.122),
    TaxBracket(min_income=164525, max_income=None,   rate=0.1405),
]

# Nunavut
NU_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=53268,  rate=0.04),
    TaxBracket(min_income=53268,  max_income=106537, rate=0.07),
    TaxBracket(min_income=106537, max_income=173205, rate=0.09),
    TaxBracket(min_income=173205, max_income=None,   rate=0.115),
]

# Ontario
ON_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=51446,  rate=0.0505),
    TaxBracket(min_income=51446,  max_income=102894, rate=0.0915),
    TaxBracket(min_income=102894, max_income=150000, rate=0.1116),
    TaxBracket(min_income=150000, max_income=220000, rate=0.1216),
    TaxBracket(min_income=220000, max_income=None,   rate=0.1316),
]

# Prince Edward Island
PE_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=32656,  rate=0.098),
    TaxBracket(min_income=32656,  max_income=64313,  rate=0.138),
    TaxBracket(min_income=64313,  max_income=105000, rate=0.167),
    TaxBracket(min_income=105000, max_income=140000, rate=0.1837),
    TaxBracket(min_income=140000, max_income=None,   rate=0.1865),
]

# Quebec
QC_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=51780,  rate=0.14),
    TaxBracket(min_income=51780,  max_income=103545, rate=0.19),
    TaxBracket(min_income=103545, max_income=126000, rate=0.24),
    TaxBracket(min_income=126000, max_income=None,   rate=0.2575),
]

# Saskatchewan
SK_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=52057,  rate=0.105),
    TaxBracket(min_income=52057,  max_income=148734, rate=0.125),
    TaxBracket(min_income=148734, max_income=None,   rate=0.145),
]

# Yukon
YT_BRACKETS_2024 = [
    TaxBracket(min_income=0,      max_income=55867,  rate=0.064),
    TaxBracket(min_income=55867,  max_income=111733, rate=0.09),
    TaxBracket(min_income=111733, max_income=154906, rate=0.109),
    TaxBracket(min_income=154906, max_income=500000, rate=0.128),
    TaxBracket(min_income=500000, max_income=None,   rate=0.15),
]


# ---------------------------------------------------------------------------
# Provincial / territorial basic personal amounts for 2024
# ---------------------------------------------------------------------------

PROVINCIAL_BASIC_PERSONAL_AMOUNTS_2024: dict[str, float] = {
    "AB": 21003.0,
    "BC": 12580.0,
    "MB": 15780.0,
    "NB": 13044.0,
    "NL": 10818.0,
    "NS": 8481.0,
    "NT": 16593.0,
    "NU": 17925.0,
    "ON": 11865.0,
    "PE": 12000.0,
    "QC": 17183.0,
    "SK": 17661.0,
    "YT": 15705.0,
}


# ---------------------------------------------------------------------------
# Lookup dictionaries for bracket sets
# ---------------------------------------------------------------------------

PROVINCIAL_BRACKETS_2024: dict[str, list[TaxBracket]] = {
    "AB": AB_BRACKETS_2024,
    "BC": BC_BRACKETS_2024,
    "MB": MB_BRACKETS_2024,
    "NB": NB_BRACKETS_2024,
    "NL": NL_BRACKETS_2024,
    "NS": NS_BRACKETS_2024,
    "NT": NT_BRACKETS_2024,
    "NU": NU_BRACKETS_2024,
    "ON": ON_BRACKETS_2024,
    "PE": PE_BRACKETS_2024,
    "QC": QC_BRACKETS_2024,
    "SK": SK_BRACKETS_2024,
    "YT": YT_BRACKETS_2024,
}
