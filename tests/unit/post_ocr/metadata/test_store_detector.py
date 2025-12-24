import pytest
from src.post_ocr.metadata.store_detector import StoreDetector

@pytest.fixture
def detector():
    return StoreDetector()

def test_detect_known_brand_lidl(detector):
    texts = ["LIDL Digital", "Strasse 1", "Berlin"]
    result = detector.detect(texts)
    assert result.name == "Lidl"
    assert result.brand == "Lidl"
    # Бренд найден в заголовке - высокая уверенность (>= 0.9)
    assert result.confidence >= 0.9

def test_detect_known_brand_rewe(detector):
    texts = ["REWE Markt", "Vielen Dank"]
    result = detector.detect(texts)
    assert result.name == "REWE"

def test_fallback_to_first_line(detector):
    # Если бренда нет в базе, берем первую значащую строку
    texts = ["Cafe Paris", "Rue de Rivoli", "75001 Paris"]
    result = detector.detect(texts)
    assert result.name == "Cafe Paris"
    assert result.brand is None
    assert result.confidence == 0.5

def test_blacklist_ignored(detector):
    texts = ["TAX INVOICE", "Super Shop", "Address 1"]
    result = detector.detect(texts)
    # TAX INVOICE должен быть пропущен (blacklist)
    assert result.name == "Super Shop"

def test_price_lines_ignored(detector):
    texts = ["9.99 EUR", "Item Name", "Address"]
    result = detector.detect(texts)
    # Строка с ценой должна быть проигнорирована
    assert result.name == "Item Name"

def test_unknown_store(detector):
    texts = ["+========+", "12345", "!!!"]
    result = detector.detect(texts)
    assert result.name == "Unknown"
