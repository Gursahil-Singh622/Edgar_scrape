from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
from tqdm import tqdm

from table_cleaner import clean_dataframe
from table_classifier import Classification, classify_table, guess_section
from utils import html_hash, normalize_whitespace


LOGGER = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    table_number: int
    dataframe: pd.DataFrame
    raw_html: str
    html_table_hash: str
    source_order: int
    classification: Classification
    extraction_notes: str


class TableExtractor:
    def extract(self, html: str) -> list[ExtractedTable]:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")
        extracted: list[ExtractedTable] = []
        section_context: str | None = None
        seen_hashes: set[str] = set()

        for source_order, table in enumerate(tqdm(tables, desc="Extracting tables", unit="table"), start=1):
            nearby_text = self._nearby_text(table)
            section_context = guess_section(nearby_text) or section_context
            raw_html = str(table)
            table_hash = html_hash(raw_html)
            try:
                parsed = pd.read_html(StringIO(raw_html), flavor="lxml")
                if not parsed:
                    raise ValueError("pandas.read_html returned no tables")
                dataframe = clean_dataframe(parsed[0])
                if dataframe.empty:
                    notes = "Skipped empty table after cleaning"
                    LOGGER.info(notes)
                    continue
                table_text = normalize_whitespace(table.get_text(" ")) or ""
                classification = classify_table(str(table_text), nearby_text, section_context)
                notes = "duplicate_html_table_hash" if table_hash in seen_hashes else ""
                seen_hashes.add(table_hash)
                extracted.append(
                    ExtractedTable(
                        table_number=len(extracted) + 1,
                        dataframe=dataframe,
                        raw_html=raw_html,
                        html_table_hash=table_hash,
                        source_order=source_order,
                        classification=classification,
                        extraction_notes=notes,
                    )
                )
            except Exception as exc:
                LOGGER.warning("Skipping table %s because it could not be parsed: %s", source_order, exc)
                continue

        return extracted

    def _nearby_text(self, table: Tag, max_chars: int = 4000) -> str:
        pieces: list[str] = []
        node = table.previous_element
        while node and len(" ".join(pieces)) < max_chars:
            if isinstance(node, Tag) and node.name in {"table", "script", "style"}:
                node = node.previous_element
                continue
            text = ""
            if isinstance(node, str):
                text = normalize_whitespace(node) or ""
            elif isinstance(node, Tag) and node.name in {"p", "div", "span", "font", "b", "strong", "h1", "h2", "h3"}:
                text = normalize_whitespace(node.get_text(" ")) or ""
            if text:
                pieces.append(text)
            node = node.previous_element
        return "\n".join(reversed(pieces))[-max_chars:]
