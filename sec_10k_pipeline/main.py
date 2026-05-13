from __future__ import annotations

import argparse
import logging
from pathlib import Path

from database import Database
from filing_finder import FilingFinder
from html_downloader import HTMLDownloader
from sec_client import SECClient
from table_extractor import TableExtractor
from xbrl_client import XBRLClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and catalog every HTML table from an SEC EDGAR 10-K filing.")
    parser.add_argument("--ticker", required=True, help="Company ticker, e.g. AAPL")
    parser.add_argument("--year", required=True, type=int, help="Fiscal year to find, e.g. 2023")
    parser.add_argument("--db", default="sec_10k_tables.db", help="SQLite DB path or SQLAlchemy connection URL")
    parser.add_argument("--include-xbrl", action="store_true", help="Store supplemental SEC companyfacts rows for the year")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(name)s: %(message)s")

    if "://" not in args.db:
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    client = SECClient()
    finder = FilingFinder(client)
    downloader = HTMLDownloader(client)
    extractor = TableExtractor()
    database = Database(args.db)

    filing = finder.find_10k(args.ticker, args.year)
    html = downloader.download(filing.filing_url)
    extracted_tables = extractor.extract(html)

    filing_id = database.insert_filing(filing)
    database.save_extracted_tables(filing_id, filing.ticker, filing.fiscal_year, extracted_tables)

    xbrl_count = 0
    if args.include_xbrl:
        xbrl_count = XBRLClient(client).store_facts_for_year(database, filing_id, filing.cik, filing.fiscal_year)

    financial_count = sum(1 for table in extracted_tables if table.classification.financial_statement_flag)
    print("SEC 10-K table extraction complete")
    print(f"Company: {filing.company_name}")
    print(f"Ticker: {filing.ticker}")
    print(f"CIK: {filing.cik}")
    print(f"Filing date: {filing.filing_date}")
    print(f"Accession number: {filing.accession_number}")
    print(f"Tables extracted: {len(extracted_tables)}")
    print(f"Financial statement tables: {financial_count}")
    if args.include_xbrl:
        print(f"Supplemental XBRL facts stored: {xbrl_count}")
    print(f"Database: {args.db}")


if __name__ == "__main__":
    main()
