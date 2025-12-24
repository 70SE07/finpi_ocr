import re
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger

@dataclass
class AddressResult:
    """Результат поиска адреса."""
    address: Optional[str] = None
    confidence: float = 0.0
    country_hint: Optional[str] = None

class AddressExtractor:
    """
    Системный экстрактор адресов.
    Ищет почтовые индексы и ключевые слова (улицы) для разных стран.
    """

    # Шаблоны почтовых индексов
    ZIP_PATTERNS = {
        "DE": r"\b\d{5}",                 # Aggressive: boundary + 5 digits (handles 514910verath)
        "UA": r"\b\d{5}\b",               # 12345 (Ukraine)
        "PL": r"\b\d{2}-\d{3}\b",         # 00-000 (Poland)
        "PT": r"\b\d{4}-\d{3}\b",         # 0000-000 (Portugal)
    }

    # Ключевые слова адресов
    STREET_KEYWORDS = [
        r"\bstr\b", r"strasse", r"straße", r"str\s*\.", 
        r"\bul\b", r"вул\s*\.", r"ул\s*\.", r"бул\s*\.", r"просп\s*\.", r"пр-т",
        r"avenida", r"ave\s*\.",
        r"plaz", r"platz", r"square", r"road", r"rd\s*\.", r"auel\b"
    ]
    
    # Паттерн для поиска телефонов (используем тот же что в RequisitesExtractor)
    PHONE_PATTERN = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"

    def extract(self, texts: List[str]) -> AddressResult:
        """
        Ищет адрес в тексте чека.
        Обычно адрес находится в первых 10-15 строках или в самом конце.
        """
        # Собираем все кандидаты
        candidates = []

        # 1. Поиск по индексам
        for i, text in enumerate(texts[:15]):
            for country, pattern in self.ZIP_PATTERNS.items():
                if re.search(pattern, text):
                    logger.debug(f"[AddressExtractor] Найден индекс ({country}) в строке: '{text}'")
                    address_lines = []
                    # Контекст сверху
                    if i > 0 and any(re.search(kw, texts[i-1].lower()) for kw in self.STREET_KEYWORDS):
                        address_lines.append(texts[i-1].strip())
                    address_lines.append(text.strip())
                    # Контекст снизу
                    if i < len(texts) - 1 and len(texts[i+1].strip()) < 30 and not re.search(r"\d", texts[i+1]):
                        if any(c.isupper() for c in texts[i+1]):
                            address_lines.append(texts[i+1].strip())
                    
                    full_addr = ", ".join(address_lines)
                    candidates.append(AddressResult(address=full_addr, confidence=0.85, country_hint=country))

        # 2. Поиск по ключевым словам (если индексов мало или нужно дополнить)
        for i, text in enumerate(texts[:15]):
            if any(re.search(kw, text.lower()) for kw in self.STREET_KEYWORDS):
                logger.debug(f"[AddressExtractor] Найдена улица (fallback): '{text}'")
                # Если эта строка еще не вошла в кандидаты по индексам
                if not any(text.strip() in c.address for c in candidates if c.address):
                    candidates.append(AddressResult(address=text.strip(), confidence=0.6))

        if not candidates:
            return AddressResult()

        # Логика выбора: обычно адрес МАГАЗИНА находится ниже адреса HQ
        # Или содержит более специфичные слова (ул. vs бул.)
        best = candidates[0]
        for c in candidates:
            # Приоритет ул. над бул. (часто ул. - это магазин, а бул. - центральный офис)
            if "ул" in c.address.lower() and "бул" not in c.address.lower():
                best = c
                break
            # Если оба одинакового типа, берем тот, что ниже в чеке (обычно это филиал)
            best = c

        logger.debug(f"[AddressExtractor] Выбран лучший кандидат: {best.address}")
        
        # Очищаем адрес от телефонов (они должны быть в RequisitesExtractor)
        if best.address:
            best.address = self._clean_phone_from_address(best.address)
            logger.debug(f"[AddressExtractor] Адрес очищен от телефонов: {best.address}")
        
        return best
    
    def _clean_phone_from_address(self, address: str) -> str:
        """
        Удаляет телефонные номера из адреса.
        Телефоны должны извлекаться отдельно через RequisitesExtractor.
        """
        if not address:
            return address
        
        # Удаляем телефоны (включая префиксы типа BG, EMK: и т.д.)
        # Паттерн для поиска телефонов с возможными префиксами
        phone_patterns = [
            # С явными префиксами: EMK: 130007884, Tel. 123456, телефон 123456
            r"\b(?:EMK|TEL|Tel|тел|телефон|Phone|phone|HOMEP)[\s:\.]*\d{7,}\b",
            # Код страны (2 буквы) + длинный номер: BG130007884, DE1234567890
            r"\b[A-Z]{2}\d{8,}\b",
            # Очень длинные последовательности цифр (10+), вероятно телефоны (но не индексы)
            # Индексы обычно 4-6 цифр, телефоны - 8-12
            r"\b\d{10,}\b",
        ]
        
        cleaned = address
        for pattern in phone_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
        # Удаляем множественные пробелы и запятые в начале/конце
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r",\s*,", ",", cleaned)  # Удаляем двойные запятые
        cleaned = cleaned.strip().strip(",").strip()
        
        return cleaned
