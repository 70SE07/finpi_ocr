import pytest
from src.post_ocr.metadata.total_extractor import TotalExtractor

@pytest.fixture
def extractor():
    return TotalExtractor()

def test_extract_standard_total(extractor):
    texts = ["REWE", "SUMME EUR 12.50", "Vielen Dank"]
    result = extractor.extract(texts)
    assert result.amount == 12.50
    assert result.confidence >= 0.9

def test_priority_ranking(extractor):
    # Проверяем, что TOTAL (priority) выигрывает у обычного числа
    texts = ["Item 1  1.99", "TOTAL   5.00", "Card #1234"]
    result = extractor.extract(texts)
    assert result.amount == 5.00

def test_cyrillic_total(extractor):
    texts = ["Сільпо", "СУМА   150.00", "ПДВ 20%"]
    result = extractor.extract(texts)
    assert result.amount == 150.00

def test_fallback_max(extractor):
    # Если ключевых слов нет, берем максимум
    texts = ["Just numbers", "10.00", "45.99", "5.00"]
    result = extractor.extract(texts)
    assert result.amount == 45.99
    assert result.confidence == 0.4

def test_noise_filtered(extractor):
    # Игнорируем номера карт (#) и проценты (%)
    texts = ["SUMME 10.00", "Card #1234.56", "Discount 10%"]
    result = extractor.extract(texts)
    assert result.amount == 10.00

def test_no_amount_found(extractor):
    texts = ["No prices here", "Just text"]
    result = extractor.extract(texts)
    assert result.amount is None
