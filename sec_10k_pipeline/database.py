from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    inspect,
    select,
)
from sqlalchemy.engine import Engine

from filing_finder import FilingMetadata
from table_extractor import ExtractedTable
from utils import make_extracted_table_name, sanitize_sql_identifier


metadata = MetaData()

filings = Table(
    "filings",
    metadata,
    Column("filing_id", Integer, primary_key=True, autoincrement=True),
    Column("ticker", String(16), nullable=False),
    Column("cik", String(10), nullable=False),
    Column("company_name", Text, nullable=False),
    Column("form_type", String(16), nullable=False),
    Column("fiscal_year", Integer, nullable=False),
    Column("filing_date", String(16), nullable=False),
    Column("accession_number", String(32), nullable=False),
    Column("primary_document", Text, nullable=False),
    Column("filing_url", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

table_catalog = Table(
    "table_catalog",
    metadata,
    Column("catalog_id", Integer, primary_key=True, autoincrement=True),
    Column("filing_id", Integer, ForeignKey("filings.filing_id"), nullable=False),
    Column("table_number", Integer, nullable=False),
    Column("sql_table_name", String(128), nullable=False),
    Column("table_title_guess", Text),
    Column("section_guess", Text),
    Column("table_type_guess", String(64), nullable=False),
    Column("financial_statement_flag", Boolean, nullable=False),
    Column("row_count", Integer, nullable=False),
    Column("column_count", Integer, nullable=False),
    Column("source_order", Integer, nullable=False),
    Column("html_table_hash", String(64), nullable=False),
    Column("extraction_notes", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

xbrl_facts = Table(
    "xbrl_facts",
    metadata,
    Column("fact_id", Integer, primary_key=True, autoincrement=True),
    Column("filing_id", Integer, ForeignKey("filings.filing_id"), nullable=False),
    Column("cik", String(10), nullable=False),
    Column("taxonomy", String(64)),
    Column("concept", String(256)),
    Column("label", Text),
    Column("description", Text),
    Column("unit", String(64)),
    Column("fiscal_year", Integer),
    Column("fiscal_period", String(16)),
    Column("form", String(16)),
    Column("filed_date", String(16)),
    Column("value", Text),
)


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.engine = create_engine(_connection_url(db_path), future=True)
        metadata.create_all(self.engine)

    def insert_filing(self, filing: FilingMetadata) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(
                filings.insert().values(
                    ticker=filing.ticker,
                    cik=filing.cik,
                    company_name=filing.company_name,
                    form_type=filing.form_type,
                    fiscal_year=filing.fiscal_year,
                    filing_date=filing.filing_date,
                    accession_number=filing.accession_number,
                    primary_document=filing.primary_document,
                    filing_url=filing.filing_url,
                )
            )
            return int(result.inserted_primary_key[0])

    def save_extracted_tables(
        self,
        filing_id: int,
        ticker: str,
        fiscal_year: int,
        extracted_tables: list[ExtractedTable],
    ) -> list[str]:
        self._validate_sequential_numbers(extracted_tables)
        saved_names: list[str] = []
        with self.engine.begin() as conn:
            for extracted in extracted_tables:
                table_name = make_extracted_table_name(ticker, fiscal_year, extracted.table_number)
                table_name = self._unique_table_name(table_name, conn)
                extracted.dataframe.to_sql(table_name, conn, if_exists="replace", index=False)
                cls = extracted.classification
                conn.execute(
                    table_catalog.insert().values(
                        filing_id=filing_id,
                        table_number=extracted.table_number,
                        sql_table_name=table_name,
                        table_title_guess=cls.table_title_guess,
                        section_guess=cls.section_guess,
                        table_type_guess=cls.table_type_guess,
                        financial_statement_flag=cls.financial_statement_flag,
                        row_count=len(extracted.dataframe),
                        column_count=len(extracted.dataframe.columns),
                        source_order=extracted.source_order,
                        html_table_hash=extracted.html_table_hash,
                        extraction_notes=extracted.extraction_notes,
                    )
                )
                saved_names.append(table_name)
        self.validate_catalog(filing_id, saved_names)
        return saved_names

    def validate_catalog(self, filing_id: int, table_names: list[str]) -> None:
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())
        missing = [name for name in table_names if name not in existing_tables]
        if missing:
            raise RuntimeError(f"Extracted SQL tables missing after save: {missing}")
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(table_catalog.c.table_number, table_catalog.c.sql_table_name)
                .where(table_catalog.c.filing_id == filing_id)
                .order_by(table_catalog.c.table_number)
            ).all()
        numbers = [row.table_number for row in rows]
        expected = list(range(1, len(rows) + 1))
        if numbers != expected:
            raise RuntimeError(f"Catalog table numbers are not sequential: {numbers}")
        catalog_names = {row.sql_table_name for row in rows}
        unmatched = [name for name in table_names if name not in catalog_names]
        if unmatched:
            raise RuntimeError(f"Extracted SQL tables have no catalog row: {unmatched}")

    def _unique_table_name(self, table_name: str, conn: Any) -> str:
        inspector = inspect(conn)
        existing = set(inspector.get_table_names())
        if table_name not in existing:
            return table_name
        suffix = 2
        while f"{table_name}_{suffix}" in existing:
            suffix += 1
        return sanitize_sql_identifier(f"{table_name}_{suffix}", max_length=128)

    @staticmethod
    def _validate_sequential_numbers(extracted_tables: list[ExtractedTable]) -> None:
        numbers = [table.table_number for table in extracted_tables]
        expected = list(range(1, len(extracted_tables) + 1))
        if numbers != expected:
            raise ValueError(f"Extracted table numbers must be sequential: {numbers}")


def _connection_url(db_path: str) -> str:
    if "://" in db_path:
        return db_path
    return f"sqlite:///{Path(db_path)}"
