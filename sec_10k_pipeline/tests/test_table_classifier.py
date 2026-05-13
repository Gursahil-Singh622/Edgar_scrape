from table_classifier import classify_table, guess_section, guess_table_type


def test_income_statement_classification():
    assert guess_table_type("consolidated statements of operations net income earnings per share") == "income_statement"


def test_section_guessing():
    text = "Item 1. Business\nSome text\nItem 7. Management's Discussion and Analysis"
    assert guess_section(text) == "Item 7. MD&A"


def test_classification_sets_financial_statement_flag():
    classification = classify_table("total assets total liabilities balance sheets")
    assert classification.table_type_guess == "balance_sheet"
    assert classification.financial_statement_flag is True
