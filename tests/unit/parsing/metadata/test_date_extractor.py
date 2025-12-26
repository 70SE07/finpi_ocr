import pytest
from datetime import datetime
from src.parsing.metadata.date_extractor import DateExtractor

@pytest.fixture
def extractor():
    return DateExtractor()

def test_extract_germany_dot_format(extractor):
    texts = ["REWE Markt GmbH", "Datum: 24.12.2024", "Summe: 10.50"]
    result = extractor.extract(texts)
    assert result.date == datetime(2024, 12, 24)
    assert result.confidence >= 0.9

def test_extract_ua_format_with_spaces(extractor):
    texts = ["Сільпо", "24 . 12 . 2024", "Сума: 120.00"]
    result = extractor.extract(texts)
    assert result.date == datetime(2024, 12, 24)

def test_extract_portugal_slash_format(extractor):
    texts = ["Pingo Doce", "Data: 24/12/24", "Total: 5.00"]
    result = extractor.extract(texts)
    assert result.date == datetime(2024, 12, 24)

def test_extract_iso_format(extractor):
    texts = ["Migros", "2024-12-24", "Tutar: 50.00"]
    result = extractor.extract(texts)
    assert result.date == datetime(2024, 12, 24)

def test_future_date_rejected(extractor):
    # Тест на лимит из settings (MAX_YEAR_OFFSET_FUTURE = 1)
    future_year = datetime.now().year + 5
    texts = [f"Future Shop", f"Date: 24.12.{future_year}"]
    result = extractor.extract(texts)
    assert result.date is None

def test_no_date_found(extractor):
    texts = ["Just some text", "No numbers here"]
    result = extractor.extract(texts)
    assert result.date is None
    assert result.confidence == 0.0
