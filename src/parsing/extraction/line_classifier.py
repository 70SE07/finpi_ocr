from enum import Enum
from typing import Optional, List, TYPE_CHECKING
import re
from loguru import logger

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

class LineType(Enum):
    ITEM = "item"
    TOTAL = "total"
    DISCOUNT = "discount"
    TAX_INFO = "tax_info"
    NOISE = "noise"

class LineClassifier:
    """
    Элемент-функция: Определяет тип строки чека.
    
    Поддерживает LocaleConfig для локализации ключевых слов.
    """
    
    def __init__(self, locale_config: Optional['LocaleConfig'] = None):
        """
        Args:
            locale_config: Конфигурация локали (опционально)
        """
        self.locale_config = locale_config
        
        # Fallback - если нет locale_config, используем немецкие ключевые слова
        if locale_config and locale_config.patterns:
            self.total_keywords = locale_config.patterns.total_keywords
            self.discount_keywords = locale_config.patterns.discount_keywords
            self.noise_keywords = locale_config.patterns.noise_keywords
            logger.debug(f"[LineClassifier] Используем ключевые слова из {locale_config.code}")
        else:
            self.total_keywords = ["gesamtbetrag", "summe", "total", "zu zahlen", "belegsumme"]
            self.discount_keywords = ["preisvorteil", "rabatt", "nachlass", "aktionsnachlass", "coupon"]
            self.noise_keywords = ["tel.", "fax.", "obj.-nr.", "terminal", "beleg-nr.", "datum", "uhrzeit"]
            logger.debug("[LineClassifier] Используем fallback ключевые слова")

    def classify(self, text: str, has_price: bool = False, has_qty: bool = False) -> LineType:
        """
        ЦКП: Тип строки (LineType).
        """
        if not text:
            return LineType.NOISE
            
        lower_text = text.lower()
        
        # 1. Проверка на итог (обычно есть ключевое слово + цена)
        if any(kw in lower_text for kw in self.total_keywords) and has_price:
            return LineType.TOTAL
            
        # 2. Проверка на скидку
        if any(kw in lower_text for kw in self.discount_keywords):
            return LineType.DISCOUNT
            
        # 3. Проверка на явный шум (адреса, телефоны)
        if any(kw in lower_text for kw in self.noise_keywords):
            return LineType.NOISE
            
        # 4. Если есть цена, но не итог и не шум — скорее всего товар
        if has_price:
            return LineType.ITEM
            
        # 5. Если ничего не подошло — шум
        return LineType.NOISE


