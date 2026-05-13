from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import insert

from config import settings
from database import Database, xbrl_facts
from sec_client import SECClient


LOGGER = logging.getLogger(__name__)


class XBRLClient:
    """Optional supplemental companyfacts fetcher for standardized fact validation."""

    def __init__(self, client: SECClient) -> None:
        self.client = client

    def fetch_companyfacts(self, cik: str) -> dict[str, Any]:
        url = f"{settings.sec_data_url}/api/xbrl/companyfacts/CIK{cik}.json"
        return self.client.get_json(url)

    def store_facts_for_year(self, database: Database, filing_id: int, cik: str, fiscal_year: int) -> int:
        try:
            payload = self.fetch_companyfacts(cik)
        except Exception as exc:
            LOGGER.warning("Could not fetch supplemental XBRL companyfacts for CIK %s: %s", cik, exc)
            return 0

        rows: list[dict[str, Any]] = []
        facts = payload.get("facts", {})
        for taxonomy, concepts in facts.items():
            for concept, concept_payload in concepts.items():
                label = concept_payload.get("label")
                description = concept_payload.get("description")
                units = concept_payload.get("units", {})
                for unit, values in units.items():
                    for value in values:
                        if value.get("fy") != fiscal_year or value.get("form") != "10-K":
                            continue
                        rows.append(
                            {
                                "filing_id": filing_id,
                                "cik": cik,
                                "taxonomy": taxonomy,
                                "concept": concept,
                                "label": label,
                                "description": description,
                                "unit": unit,
                                "fiscal_year": value.get("fy"),
                                "fiscal_period": value.get("fp"),
                                "form": value.get("form"),
                                "filed_date": value.get("filed"),
                                "value": str(value.get("val")),
                            }
                        )

        if not rows:
            return 0
        with database.engine.begin() as conn:
            conn.execute(insert(xbrl_facts), rows)
        return len(rows)
