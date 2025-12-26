import re
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
from loguru import logger
from .address_extractor import AddressResult

from config.settings import (
    STORE_SCAN_LIMIT, STORE_FALLBACK_LIMIT, MIN_STORE_NAME_LENGTH,
    STORE_CONFIDENCE_HIGH
)

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

@dataclass
class StoreResult:
    """Результат определения магазина."""
    name: str
    brand: Optional[str] = None
    confidence: float = 0.0

class StoreDetector:
    """
    Определяет магазин по тексту чека.
    Использует базу известных брендов и ключевых слов.
    
    Поддерживает LocaleConfig для локализации брендов и настроек.
    """
    
    # База брендов (fallback - если нет locale_config)
    BRANDS = {
        "Lidl": [r"\blidl\b", r"\bli dl\b"],
        "Aldi": [r"\baldi\b", r"\baldi süd\b", r"\baldi nord\b"],
        "REWE": [r"\brewe\b"],
        "Edeka": [r"\bedeka\b"],
        "Penny": [r"\bpenny\b"],
        "Netto": [r"\bnetto\b(?!\s*mwst)", r"\bnetto\s+markt\b"], # Избегаем Netto MwSt
        "Kaufland": [r"\bkaufland\b"],
        "Rossmann": [r"\brossmann\b"],
        "dm": [r"\bdm-drogerie\b", r"\bdm\b"],
        "Billa": [r"\bbilla\b", r"\bбилла\b", r"\bбилл\b"],
        "Dnipro-M": [r"dnipro\s*[-–—]\s*m", r"дніпро\s*[-–—]\s*м", r"\bdniprom\b"],
        "Biedronka": [r"\bbiedronka\b"],
        "Pingo Doce": [r"\bpingo doce\b", r"\bpingo\b"],
        "Migros": [r"\bmigros\b"],
        "Carrefour": [r"\bcarrefour\b"],
        "Shell": [r"\bshell\b"],
    }

    # Слова, которые НЕ могут быть названием магазина (заголовки)
    BLACKLIST = [
        r"tax invoice", r"invoice", r"faktura", r"paragon", r"fiskalny",
        r"receipt", r"check", r"квитанция", r"чек", r"рахунок",
        r"suma", r"total", r"итого", r"оплата", r"betrag", r"summe",
        r"customer copy", r"kundenbeleg", r"schweine", r"hähn",
        r"pfand", r"rabatt", r"eur/kg", r"zaziki", r"baguette"
    ]

    def detect(
        self, 
        texts: List[str], 
        address_res: Optional[AddressResult] = None,
        locale_config: Optional['LocaleConfig'] = None
    ) -> StoreResult:
        """
        Анализирует строки чека для поиска бренда.
        Если бренд не найден, использует адрес как ориентир или fallback.
        
        Args:
            texts: Список строк чека
            address_res: Результат извлечения адреса
            locale_config: Конфигурация локали (опционально)
        """
        # Получаем настройки из locale_config или используем дефолтные
        if locale_config and locale_config.extractors:
            scan_limit = locale_config.extractors.store_detection.get("scan_limit", STORE_SCAN_LIMIT)
            fallback_limit = locale_config.extractors.store_detection.get("fallback_limit", STORE_FALLBACK_LIMIT)
            min_name_length = locale_config.extractors.store_detection.get("min_name_length", MIN_STORE_NAME_LENGTH)
            
            # Используем бренды из locale_config если они есть
            if "known_brands" in locale_config.extractors.store_detection:
                brands_dict = self._build_brands_dict(locale_config.extractors.store_detection["known_brands"])
            else:
                brands_dict = self.BRANDS
            
            logger.debug(f"[StoreDetector] Используем настройки из {locale_config.code}: scan_limit={scan_limit}")
        else:
            scan_limit = STORE_SCAN_LIMIT
            fallback_limit = STORE_FALLBACK_LIMIT
            min_name_length = MIN_STORE_NAME_LENGTH
            brands_dict = self.BRANDS
            logger.debug("[StoreDetector] Используем настройки из settings.py")
        
        # Берем первые N строк, так как название обычно в заголовке
        header_text = "\n".join(texts[:scan_limit]).lower()
        
        for brand, patterns in brands_dict.items():
            for pattern in patterns:
                if re.search(pattern, header_text, re.IGNORECASE):
                    logger.debug(f"[StoreDetector] Известный бренд найден в заголовке: {brand}")
                    return StoreResult(name=brand, brand=brand, confidence=0.95)
        
        # Второй проход: полный скан (бывает бренд внизу или в середине)
        full_text = "\n".join(texts).lower()
        for brand, patterns in brands_dict.items():
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    logger.debug(f"[StoreDetector] Известный бренд найден в теле чека: {brand}")
                    return StoreResult(name=brand, brand=brand, confidence=STORE_CONFIDENCE_HIGH)

        logger.trace("[StoreDetector] Бренд не найден, переход к Fallback-режиму")
        if address_res and address_res.address:
            # Название магазина часто находится СРАЗУ НАД адресом
            # Ищем, в какой строке был найден адрес
            addr_parts = address_res.address.split(", ")
            first_addr_line = addr_parts[0]
            for i, text in enumerate(texts[:15]):
                if first_addr_line in text and i > 0:
                    potential_name = texts[i-1].strip()
                    if potential_name and not any(re.search(bl, potential_name.lower()) for bl in self.BLACKLIST):
                         logger.debug(f"[StoreDetector] Имя магазина определено из строки НАД адресом: '{potential_name}'")
                         return StoreResult(name=potential_name, brand=None, confidence=0.7)

        # Если контекста адреса нет, пробуем взять первую значащую строку как имя
        for text in texts[:fallback_limit]:
            clean_text = text.strip()
            # Проверяем черный список
            if any(re.search(bl, clean_text.lower()) for bl in self.BLACKLIST):
                continue
                
            # Имя магазина обычно содержит буквы, не слишком короткое
            if (len(clean_text) > min_name_length and 
                re.search(r"[a-zA-Zа-яА-Я]", clean_text) and 
                not re.search(r"\d", clean_text) and # Исключаем строки с любыми цифрами
                not any(c in clean_text for c in "*@%€") and # Исключаем маркеры цены
                not clean_text.startswith("+")): # Не декор
                logger.debug(f"[StoreDetector] Имя магазина определено из строки: '{clean_text}'")
                return StoreResult(name=clean_text, brand=None, confidence=0.5)
                
        logger.warning("[StoreDetector] Не удалось определить название магазина")
        return StoreResult(name="Unknown", brand=None, confidence=0.0)
    
    def _build_brands_dict(self, brand_list: List[str]) -> dict:
        """
        Строит словарь брендов из списка.
        
        Args:
            brand_list: Список брендов из locale_config
            
        Returns:
            dict: Словарь {название: [паттерны]}
        """
        brands_dict = {}
        for brand in brand_list:
            brand_lower = brand.lower()
            brands_dict[brand] = [rf"\b{brand_lower}\b"]
        return brands_dict


