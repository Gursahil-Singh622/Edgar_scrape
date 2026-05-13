from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    sec_user_agent: str = os.getenv(
        "SEC_USER_AGENT",
        "Financial Analyst Research your.email@example.com",
    )
    sec_requests_per_second: float = float(os.getenv("SEC_REQUESTS_PER_SECOND", "8"))
    sec_base_url: str = "https://www.sec.gov"
    sec_data_url: str = "https://data.sec.gov"

    @property
    def request_delay_seconds(self) -> float:
        requests_per_second = min(max(self.sec_requests_per_second, 0.1), 9.5)
        return 1.0 / requests_per_second


settings = Settings()
