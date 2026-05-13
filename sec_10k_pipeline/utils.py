from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Iterable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_whitespace(value: object) -> object:
    if value is None:
        return value
    text = str(value)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def html_hash(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest()


def accession_no_dashes(accession_number: str) -> str:
    return accession_number.replace("-", "")


def sanitize_sql_identifier(value: str, max_length: int = 63) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "table"
    if cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    return cleaned[:max_length].rstrip("_")


def make_extracted_table_name(ticker: str, fiscal_year: int, table_number: int) -> str:
    ticker_part = sanitize_sql_identifier(ticker)
    return sanitize_sql_identifier(f"{ticker_part}_{fiscal_year}_10k_t{table_number:03d}")


def dedupe_column_names(columns: Iterable[object]) -> list[str]:
    seen: dict[str, int] = {}
    output: list[str] = []
    for index, column in enumerate(columns, start=1):
        base = sanitize_sql_identifier(str(normalize_whitespace(column) or f"column_{index}"))
        if not base or base == "nan":
            base = f"column_{index}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        output.append(base if count == 0 else f"{base}_{count + 1}")
    return output
