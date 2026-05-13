# SEC 10-K Table Pipeline

Extract and catalog every HTML table from a full SEC EDGAR 10-K filing. The pipeline is built for analysts who need more than standardized financial statements: it parses the full HTML filing so narrative, compensation, properties, risk, debt, lease, tax, segment, and other tables are captured too.

Each extracted table is saved as its own SQL table, `table_catalog` records the numbered order and metadata for every extracted table, and `table_catalog_enriched` joins that catalog to filing identity fields so multi-company databases are easy to inspect.

## What It Does

Given a ticker and fiscal year, the pipeline:

1. Converts the ticker to a CIK using SEC `company_tickers.json`.
2. Fetches SEC submissions JSON for the CIK.
3. Finds the matching 10-K accession and primary document.
4. Downloads the full 10-K HTML filing from SEC Archives.
5. Extracts every HTML table in document order.
6. Converts each table into a pandas DataFrame.
7. Lightly cleans tables without over-normalizing financial labels.
8. Stores every table as an independent SQL table.
9. Writes a master `table_catalog` with numbered table metadata.
10. Optionally stores SEC XBRL `companyfacts` rows as a supplemental validation layer.

## Install

```bash
cd sec_10k_pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure SEC User-Agent

SEC asks automated clients to identify themselves. Copy the example env file and set a real name/email before making requests:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
SEC_USER_AGENT="Your Name your.email@example.com"
SEC_REQUESTS_PER_SECOND=8
```

The default throttle stays below the SEC fair access ceiling of 10 requests per second.

## Run

```bash
python main.py --ticker AAPL --year 2023 --db sec_10k_tables.db
```

With supplemental XBRL companyfacts:

```bash
python main.py --ticker AAPL --year 2023 --db sec_10k_tables.db --include-xbrl
```

Expected console output includes company, filing ID, CIK, filing date, accession number, number of tables extracted, number of financial statement tables, database path, and the enriched catalog view name.

## Database Structure

### `filings`

One row per downloaded 10-K:

- `filing_id`
- `ticker`
- `cik`
- `company_name`
- `form_type`
- `fiscal_year`
- `filing_date`
- `accession_number`
- `primary_document`
- `filing_url`
- `created_at`

### `table_catalog`

One row per extracted HTML table:

- `catalog_id`
- `filing_id`
- `table_number`
- `sql_table_name`
- `table_title_guess`
- `section_guess`
- `table_type_guess`
- `financial_statement_flag`
- `row_count`
- `column_count`
- `source_order`
- `html_table_hash`
- `extraction_notes`
- `created_at`

### `table_catalog_enriched`

Read-only SQL view for analysis across multiple companies and years. It joins `table_catalog` to `filings`, so every catalog row includes:

- `ticker`
- `cik`
- `company_name`
- `form_type`
- `fiscal_year`
- `filing_date`
- `accession_number`

Use this view for normal analysis when one SQLite database contains multiple filings.

### Independent Extracted Tables

Each parsed table is stored independently using names such as:

- `aapl_2023_10k_t001`
- `aapl_2023_10k_t002`
- `aapl_2023_10k_t003`

### `xbrl_facts`

Optional supplemental facts from SEC companyfacts:

- `filing_id`
- `cik`
- `taxonomy`
- `concept`
- `label`
- `description`
- `unit`
- `fiscal_year`
- `fiscal_period`
- `form`
- `filed_date`
- `value`

## Table Classification

The first version uses rule-based keyword heuristics from nearby headings, section context, and table text. Categories include:

- `income_statement`
- `balance_sheet`
- `cash_flow_statement`
- `shareholders_equity`
- `segment_table`
- `debt_table`
- `lease_table`
- `tax_table`
- `revenue_table`
- `compensation_table`
- `properties_table`
- `risk_factor_table`
- `non_financial_table`
- `unknown`

The classifier is intentionally transparent and easy to extend.

## Example Queries

View the catalog:

```sql
SELECT ticker, fiscal_year, table_number, sql_table_name, section_guess, table_type_guess, row_count, column_count
FROM table_catalog_enriched
ORDER BY ticker, fiscal_year, table_number;
```

View tables for one company/year:

```sql
SELECT table_number, sql_table_name, section_guess, table_type_guess, row_count, column_count
FROM table_catalog_enriched
WHERE ticker = 'AAPL' AND fiscal_year = 2023
ORDER BY table_number;
```

Open one extracted table:

```sql
SELECT *
FROM aapl_2023_10k_t001
LIMIT 25;
```

Find likely financial statement tables:

```sql
SELECT table_number, sql_table_name, table_title_guess, table_type_guess
FROM table_catalog_enriched
WHERE financial_statement_flag = 1
ORDER BY ticker, fiscal_year, table_number;
```

Find possible duplicate HTML tables:

```sql
SELECT html_table_hash, COUNT(*) AS table_count
FROM table_catalog
GROUP BY html_table_hash
HAVING COUNT(*) > 1;
```

## Why XBRL Is Supplemental

SEC XBRL and companyfacts data are excellent for validating standardized financial facts, but they do not represent every table in a 10-K. Many useful analyst tables appear only in the HTML filing, especially narrative, compensation, properties, market-risk, schedule, and footnote tables. This project therefore uses HTML extraction as the primary source and XBRL only as an optional validation supplement.

## Limitations

HTML filings vary widely by issuer and filing year. Some tables are layout tables, some have complex row/column spans, and some filing text is embedded in ways that pandas cannot perfectly infer. The pipeline handles parse failures defensively by skipping bad tables and logging warnings, but analyst review is still recommended before using extracted tables for models or reporting.

The cleaning step is intentionally light. It removes empty rows/columns, normalizes whitespace, deduplicates column names, and preserves row order. It does not aggressively rewrite financial labels or strip footnote markers.

## Tests

```bash
pytest
```
