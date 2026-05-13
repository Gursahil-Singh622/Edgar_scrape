from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import settings
from sec_client import SECClient
from utils import accession_no_dashes


@dataclass(frozen=True)
class FilingMetadata:
    ticker: str
    cik: str
    company_name: str
    form_type: str
    fiscal_year: int
    filing_date: str
    accession_number: str
    primary_document: str
    filing_url: str


class FilingFinder:
    def __init__(self, client: SECClient) -> None:
        self.client = client

    def ticker_to_company(self, ticker: str) -> tuple[str, str]:
        url = f"{settings.sec_base_url}/files/company_tickers.json"
        mapping = self.client.get_json(url)
        ticker_upper = ticker.upper()
        for row in mapping.values():
            if row["ticker"].upper() == ticker_upper:
                cik = str(row["cik_str"]).zfill(10)
                return cik, row["title"]
        raise ValueError(f"Ticker not found in SEC company ticker mapping: {ticker}")

    def get_submissions(self, cik: str) -> dict[str, Any]:
        url = f"{settings.sec_data_url}/submissions/CIK{cik}.json"
        return self.client.get_json(url)

    def find_10k(self, ticker: str, fiscal_year: int) -> FilingMetadata:
        cik, company_name = self.ticker_to_company(ticker)
        submissions = self.get_submissions(cik)
        recent = submissions["filings"]["recent"]
        forms = recent["form"]
        accession_numbers = recent["accessionNumber"]
        filing_dates = recent["filingDate"]
        report_dates = recent.get("reportDate", [""] * len(forms))
        primary_documents = recent["primaryDocument"]

        candidates: list[tuple[int, str]] = []
        for index, form in enumerate(forms):
            if form != "10-K":
                continue
            report_year = _year_from_date(report_dates[index])
            filing_year = _year_from_date(filing_dates[index])
            if report_year == fiscal_year or filing_year == fiscal_year + 1 or filing_year == fiscal_year:
                candidates.append((index, filing_dates[index]))

        if not candidates:
            raise ValueError(f"No 10-K filing found for {ticker.upper()} fiscal year {fiscal_year}")

        index = sorted(candidates, key=lambda item: item[1])[0][0]
        accession_number = accession_numbers[index]
        primary_document = primary_documents[index]
        filing_url = (
            f"{settings.sec_base_url}/Archives/edgar/data/"
            f"{int(cik)}/{accession_no_dashes(accession_number)}/{primary_document}"
        )
        return FilingMetadata(
            ticker=ticker.upper(),
            cik=cik,
            company_name=company_name,
            form_type=forms[index],
            fiscal_year=fiscal_year,
            filing_date=filing_dates[index],
            accession_number=accession_number,
            primary_document=primary_document,
            filing_url=filing_url,
        )


def _year_from_date(value: str) -> int | None:
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
