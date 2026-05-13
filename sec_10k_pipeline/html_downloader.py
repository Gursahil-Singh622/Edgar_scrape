from __future__ import annotations

from sec_client import SECClient


class HTMLDownloader:
    def __init__(self, client: SECClient) -> None:
        self.client = client

    def download(self, filing_url: str) -> str:
        return self.client.get_text(filing_url)
