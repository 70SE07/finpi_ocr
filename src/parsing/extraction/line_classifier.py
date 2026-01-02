from enum import Enum
from typing import Optional, List, TYPE_CHECKING
import re
from loguru import logger

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

from ..locales.locale_registry import LocaleRegistry

class LineType(Enum):
    ITEM = "item"
    TOTAL = "total"
    DISCOUNT = "discount"
    TAX_INFO = "tax_info"
    NOISE = "noise"

class LineClassifier:
    """
    Определяет тип строки чека.
    
    Поддерживает LocaleConfig для локализации ключевых слов.
    """
    
    def __init__(self, locale_config: Optional['LocaleConfig'] = None):
        """
        Args:
            locale_config: Конфигурация локали (опционально)
        """
        if locale_config is None:
            registry = LocaleRegistry()
            available = registry.get_available_locales()
            
            if not available:
                raise ValueError(
                    "No locale configs available. "
                    "Create at least one config in src/parsing/locales/"
                )
            
            fallback_locale_code = available[0]
            locale_config = registry.get_locale_config(fallback_locale_code)
            
            logger.warning(
                f"[LineClassifier] No locale_config provided. "
                f"Using fallback: {fallback_locale_code}"
            )
        
        self.locale_config = locale_config
        
        if not locale_config.patterns:
            raise ValueError("Locale config patterns are required for LineClassifier")
        
        self.total_keywords = locale_config.patterns.total_keywords
        self.discount_keywords = locale_config.patterns.discount_keywords
        self.noise_keywords = locale_config.patterns.noise_keywords
        logger.debug(f"[LineClassifier] Используем ключевые слова из {locale_config.code}")

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



