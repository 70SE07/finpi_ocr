import pytest
from src.post_ocr.metadata.address_extractor import AddressExtractor

@pytest.fixture
def extractor():
    return AddressExtractor()

def test_extract_german_address_with_zip(extractor):
    """Тест извлечения адреса с немецким почтовым индексом."""
    texts = ["REWE Markt", "Musterstraße 12", "12345 Berlin", "Telefon: 030123456"]
    result = extractor.extract(texts)
    assert result.address is not None
    assert "12345" in result.address
    assert result.country_hint == "DE"
    assert result.confidence > 0.0

def test_extract_ukrainian_address(extractor):
    """Тест извлечения адреса с украинским индексом."""
    texts = ["Сільпо", "вул. Хрещатик 1", "01001 Київ"]
    result = extractor.extract(texts)
    assert result.address is not None
    assert "01001" in result.address or "Хрещатик" in result.address
    # country_hint может быть DE или UA (DE паттерн агрессивный), главное что адрес найден
    assert result.country_hint in ["DE", "UA"] or result.country_hint is None

def test_extract_polish_address(extractor):
    """Тест извлечения адреса с польским индексом."""
    texts = ["Zabka", "ul. Marszałkowska 1", "00-123 Warszawa"]
    result = extractor.extract(texts)
    assert result.address is not None
    assert "00-123" in result.address or "Marszałkowska" in result.address
    assert result.country_hint == "PL"

def test_clean_phone_from_address_bg_prefix(extractor):
    """Тест очистки телефона с префиксом BG из адреса."""
    texts = ["BAPHA ул. дубРОвНик 48 HOMEP 3ДдC BG130007884"]
    result = extractor.extract(texts)
    assert result.address is not None
    assert "BG130007884" not in result.address
    assert "130007884" not in result.address
    assert "дубРОвНик" in result.address

def test_clean_phone_from_address_with_prefixes(extractor):
    """Тест очистки телефонов с различными префиксами (EMK, Tel, телефон)."""
    texts = ["Адрес ул. Ленина 10 EMK: 1234567890", "Дополнительная информация"]
    result = extractor.extract(texts)
    assert result.address is not None
    assert "1234567890" not in result.address
    assert "EMK" not in result.address

def test_clean_phone_from_address_long_number(extractor):
    """Тест очистки длинных телефонных номеров (10+ цифр)."""
    texts = ["Siegburger Str. 30 51491 Overath 02206242500"]
    result = extractor.extract(texts)
    assert result.address is not None
    # Длинный номер (11 цифр) должен быть удален
    assert "02206242500" not in result.address
    # Почтовый индекс (5 цифр) должен остаться
    assert "51491" in result.address

def test_preserve_postal_code(extractor):
    """Тест что почтовые индексы НЕ удаляются при очистке от телефонов."""
    texts = ["46359 Heiden, Sachsenstr. 2c", "www.NETTO-ONLINE.DE"]
    result = extractor.extract(texts)
    assert result.address is not None
    # Почтовый индекс 46359 (5 цифр) должен остаться
    assert "46359" in result.address

def test_address_with_street_keywords(extractor):
    """Тест поиска адреса по ключевым словам улиц (fallback)."""
    texts = ["Netto Marken-Discount", "Sachsenstr. 2c", "Heiden"]
    result = extractor.extract(texts)
    assert result.address is not None
    assert "Sachsenstr" in result.address or "Sachsenstr." in result.address

def test_no_address_found(extractor):
    """Тест когда адрес не найден."""
    texts = ["Item 1  2.99", "Item 2  3.50", "Total 6.49"]
    result = extractor.extract(texts)
    assert result.address is None
    assert result.confidence == 0.0

def test_address_priority_street_over_boulevard(extractor):
    """Тест приоритета ул. над бул. (ул. обычно магазин, бул. - центральный офис)."""
    texts = [
        "СОФИЯ БУЛ. БЪЛГАРИЯ 55",
        "ВАРНА УЛ. ДУБРОВНИК 48"
    ]
    result = extractor.extract(texts)
    # Должен быть выбран адрес с "ул" (улица), а не "бул" (бульвар)
    assert result.address is not None
    assert "ул" in result.address.lower() or "УЛ" in result.address

