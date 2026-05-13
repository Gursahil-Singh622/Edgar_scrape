from __future__ import annotations

import pandas as pd

from utils import dedupe_column_names, normalize_whitespace


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Lightly clean an extracted table without changing analyst-facing labels."""
    cleaned = df.copy()
    cleaned = cleaned.map(normalize_whitespace)
    cleaned = cleaned.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    cleaned = cleaned.dropna(axis=0, how="all").dropna(axis=1, how="all")
    cleaned = cleaned.reset_index(drop=True)

    if cleaned.empty:
        return cleaned

    cleaned.columns = dedupe_column_names(cleaned.columns)
    return cleaned.astype("string")
