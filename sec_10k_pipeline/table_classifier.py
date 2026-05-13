from __future__ import annotations

import re
from dataclasses import dataclass


TABLE_TYPES = [
    "income_statement",
    "balance_sheet",
    "cash_flow_statement",
    "shareholders_equity",
    "segment_table",
    "debt_table",
    "lease_table",
    "tax_table",
    "revenue_table",
    "compensation_table",
    "properties_table",
    "risk_factor_table",
    "non_financial_table",
    "unknown",
]

SECTION_PATTERNS = [
    ("Item 1. Business", r"item\s+1[\.\s]+business"),
    ("Item 1A. Risk Factors", r"item\s+1a[\.\s]+risk\s+factors"),
    ("Item 2. Properties", r"item\s+2[\.\s]+properties"),
    ("Item 3. Legal Proceedings", r"item\s+3[\.\s]+legal\s+proceedings"),
    ("Item 7. MD&A", r"item\s+7[\.\s]+management'?s\s+discussion|item\s+7[\.\s]+m\s*&\s*a"),
    (
        "Item 7A. Quantitative and Qualitative Disclosures About Market Risk",
        r"item\s+7a[\.\s]+quantitative\s+and\s+qualitative",
    ),
    (
        "Item 8. Financial Statements and Supplementary Data",
        r"item\s+8[\.\s]+financial\s+statements",
    ),
    ("Item 9A. Controls and Procedures", r"item\s+9a[\.\s]+controls\s+and\s+procedures"),
    ("Item 10. Directors and Governance", r"item\s+10[\.\s]+directors"),
    ("Item 11. Executive Compensation", r"item\s+11[\.\s]+executive\s+compensation"),
    ("Item 12. Security Ownership", r"item\s+12[\.\s]+security\s+ownership"),
    ("Item 13. Certain Relationships", r"item\s+13[\.\s]+certain\s+relationships"),
    ("Item 14. Principal Accountant Fees", r"item\s+14[\.\s]+principal\s+accountant"),
    (
        "Item 15. Exhibits and Financial Statement Schedules",
        r"item\s+15[\.\s]+exhibits\s+and\s+financial\s+statement",
    ),
]


@dataclass(frozen=True)
class Classification:
    table_title_guess: str | None
    section_guess: str | None
    table_type_guess: str
    financial_statement_flag: bool


def classify_table(table_text: str, nearby_text: str = "", section_guess: str | None = None) -> Classification:
    combined = f"{nearby_text} {table_text}".lower()
    guessed_section = section_guess or guess_section(nearby_text)
    table_type = guess_table_type(combined, guessed_section)
    return Classification(
        table_title_guess=guess_title(nearby_text),
        section_guess=guessed_section,
        table_type_guess=table_type,
        financial_statement_flag=table_type
        in {"income_statement", "balance_sheet", "cash_flow_statement", "shareholders_equity"},
    )


def guess_section(text: str) -> str | None:
    lower = text.lower()
    matches: list[tuple[int, str]] = []
    for section, pattern in SECTION_PATTERNS:
        found = list(re.finditer(pattern, lower))
        if found:
            matches.append((found[-1].start(), section))
    if not matches:
        return None
    return sorted(matches, key=lambda item: item[0])[-1][1]


def guess_table_type(text: str, section_guess: str | None = None) -> str:
    rules = [
        ("cash_flow_statement", ["cash flows", "operating activities", "investing activities", "financing activities"]),
        ("income_statement", ["statements of operations", "income statements", "net income", "earnings per share"]),
        ("balance_sheet", ["balance sheets", "total assets", "total liabilities", "shareholders' equity"]),
        ("shareholders_equity", ["shareholders' equity", "stockholders' equity", "accumulated other comprehensive"]),
        ("segment_table", ["segment", "reportable segments", "geographic", "net sales by"]),
        ("debt_table", ["debt", "borrowings", "senior notes", "maturities"]),
        ("lease_table", ["lease", "right-of-use", "operating lease"]),
        ("tax_table", ["income taxes", "tax expense", "deferred tax", "effective tax rate"]),
        ("revenue_table", ["revenue", "net sales", "contract balances", "remaining performance obligations"]),
        ("compensation_table", ["compensation", "salary", "stock awards", "option awards"]),
        ("properties_table", ["properties", "square feet", "facilities", "leased and owned"]),
        ("risk_factor_table", ["risk factors", "risk", "impact", "likelihood"]),
    ]
    for table_type, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return table_type
    if section_guess == "Item 1A. Risk Factors":
        return "risk_factor_table"
    if section_guess == "Item 2. Properties":
        return "properties_table"
    if text.strip():
        return "non_financial_table"
    return "unknown"


def guess_title(nearby_text: str) -> str | None:
    lines = [line.strip() for line in re.split(r"[\r\n]+", nearby_text) if line.strip()]
    if not lines:
        return None
    candidate = lines[-1]
    return candidate[:250]
