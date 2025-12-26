import re
from decimal import Decimal, InvalidOperation
from typing import Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

class PriceParser:
    """
    Элемент-функция: Извлекает и нормализует цену из строки.
    
    Поддерживает LocaleConfig для локализации разделителей.
    """
    
    def __init__(self, locale_config: Optional['LocaleConfig'] = None):
        """
        Args:
            locale_config: Конфигурация локали (опционально)
        """
        self.locale_config = locale_config
        # Регулярка для цены: число с запятой или точкой перед концом строки или после пробела
        # Приоритет: правая часть строки (Right-to-Left logic)
        self.price_pattern = re.compile(r'(-?\d+[\.,]\d{2})(?!\d)')

    def parse(self, text: str) -> Optional[Decimal]:
        """
        ЦКП: Нормализованная цена (Decimal) или None.
        Ищет последнюю валидную цену в строке.
        
        Args:
            text: Текстовая строка
            
        Returns:
            Decimal: Цена или None
        """
        if not text:
            return None
            
        # Очистка от лишних символов в конце (напр. налоги A, B)
        clean_text = text.strip()
        
        # Защита от дат и времени (уже реализовано в ContextLine, переносим сюда)
        if self._is_date_or_time(clean_text):
            return None

        matches = self.price_pattern.findall(clean_text)
        if not matches:
            return None
            
        # Берем последнюю цену (Right-to-Left)
        raw_price = matches[-1]
        
        try:
            # Нормализация с учетом locale_config
            normalized = self._normalize_price(raw_price)
            return Decimal(normalized)
        except (InvalidOperation, ValueError):
            logger.warning(f"[PriceParser] Ошибка нормализации цены: {raw_price}")
            return None
    
    def _normalize_price(self, raw_price: str) -> str:
        """
        Нормализует цену с учетом разделителей из locale_config.
        
        Примеры:
        - Германия: "1,99" → "1.99"
        - США: "1.99" → "1.99"
        """
        if self.locale_config and self.locale_config.currency:
            dec_sep = self.locale_config.currency.decimal_separator
            thou_sep = self.locale_config.currency.thousands_separator
            
            # Убираем thousands separator
            if thou_sep in raw_price:
                raw_price = raw_price.replace(thou_sep, "")
            
            # Заменяем decimal separator на точку
            if dec_sep == ",":
                return raw_price.replace(",", ".")
            elif dec_sep == "." and "," in raw_price:
                # В случае "," это не decimal separator (ошибка в locale_config или OCR)
                # Логируем и пробуем разные варианты
                logger.trace(f"[PriceParser] Конфликт разделителей в {raw_price}")
                # Убираем запятые, оставляем точку
                raw_price = raw_price.replace(",", "")
        
        # Fallback: если нет locale_config - заменяем запятую на точку (германский формат)
        return raw_price.replace(',', '.')

    def _is_date_or_time(self, text: str) -> bool:
        """Проверка на паттерны даты/времени, чтобы не принять их за цену."""
        date_patterns = [
            r'\d{2}\.\d{2}\.\d{2,4}',  # 24.12.2025
            r'\d{2}:\d{2}:\d{2}',      # 18:05:00
            r'\d{2}:\d{2}'             # 18:05
        ]
        for p in date_patterns:
            if re.search(p, text):
                return True
        return False


