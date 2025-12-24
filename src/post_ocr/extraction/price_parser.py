import re
from decimal import Decimal, InvalidOperation
from typing import Optional
from loguru import logger

class PriceParser:
    """Элемент-функция: Извлекает и нормализует цену из строки."""
    
    def __init__(self):
        # Регулярка для цены: число с запятой или точкой перед концом строки или после пробела
        # Приоритет: правая часть строки (Right-to-Left logic)
        self.price_pattern = re.compile(r'(-?\d+[\.,]\d{2})(?!\d)')

    def parse(self, text: str) -> Optional[Decimal]:
        """
        ЦКП: Нормализованная цена (Decimal) или None.
        Ищет последнюю валидную цену в строке.
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
            # Нормализация: замена запятой на точку
            normalized = raw_price.replace(',', '.')
            return Decimal(normalized)
        except (InvalidOperation, ValueError):
            logger.warning(f"[PriceParser] Ошибка нормализации цены: {raw_price}")
            return None

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
