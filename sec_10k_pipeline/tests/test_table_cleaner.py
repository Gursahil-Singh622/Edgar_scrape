import pandas as pd

from table_cleaner import clean_dataframe
from utils import sanitize_sql_identifier


def test_sanitize_sql_identifier():
    assert sanitize_sql_identifier("AAPL 2023 10-K T001") == "aapl_2023_10_k_t001"
    assert sanitize_sql_identifier("123 bad/name") == "t_123_bad_name"


def test_clean_dataframe_removes_empty_rows_columns_and_dedupes_headers():
    df = pd.DataFrame(
        [
            [" Revenue ", " Revenue ", None],
            ["  $1  ", " $2 ", None],
            [None, None, None],
        ],
        columns=[" Metric ", " Metric ", " "],
    )
    cleaned = clean_dataframe(df)
    assert list(cleaned.columns) == ["metric", "metric_2"]
    assert cleaned.shape == (2, 2)
    assert cleaned.iloc[0, 0] == "Revenue"
