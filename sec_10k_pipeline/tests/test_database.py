import pandas as pd
from sqlalchemy import text

from database import Database
from filing_finder import FilingMetadata
from table_classifier import Classification
from table_extractor import ExtractedTable


def _filing() -> FilingMetadata:
    return FilingMetadata(
        ticker="AAPL",
        cik="0000320193",
        company_name="Apple Inc.",
        form_type="10-K",
        fiscal_year=2023,
        filing_date="2023-11-03",
        accession_number="0000320193-23-000106",
        primary_document="aapl-20230930.htm",
        filing_url="https://www.sec.gov/example",
    )


def _table(number: int) -> ExtractedTable:
    return ExtractedTable(
        table_number=number,
        dataframe=pd.DataFrame({"label": ["Revenue"], "value": ["100"]}),
        raw_html="<table><tr><td>Revenue</td><td>100</td></tr></table>",
        html_table_hash=f"hash-{number}",
        source_order=number,
        classification=Classification(
            table_title_guess="Revenue",
            section_guess="Item 8. Financial Statements and Supplementary Data",
            table_type_guess="revenue_table",
            financial_statement_flag=False,
        ),
        extraction_notes="",
    )


def test_catalog_row_creation_and_sequential_numbering(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    filing_id = db.insert_filing(_filing())
    names = db.save_extracted_tables(filing_id, "AAPL", 2023, [_table(1), _table(2)])
    assert names == ["aapl_2023_10k_t001", "aapl_2023_10k_t002"]
    db.validate_catalog(filing_id, names)


def test_enriched_catalog_view_includes_filing_identity(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    filing_id = db.insert_filing(_filing())
    db.save_extracted_tables(filing_id, "AAPL", 2023, [_table(1)])
    with db.engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT ticker, company_name, fiscal_year, accession_number, table_number, sql_table_name
                FROM table_catalog_enriched
                """
            )
        ).one()
    assert row.ticker == "AAPL"
    assert row.company_name == "Apple Inc."
    assert row.fiscal_year == 2023
    assert row.table_number == 1


def test_rejects_non_sequential_tables(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    filing_id = db.insert_filing(_filing())
    try:
        db.save_extracted_tables(filing_id, "AAPL", 2023, [_table(2)])
    except ValueError as exc:
        assert "sequential" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-sequential table numbers")
