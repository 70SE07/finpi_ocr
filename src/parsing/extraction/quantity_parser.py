import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

@dataclass
class QtyResult:
    qty: Decimal
    unit_price: Optional[Decimal] = None
    raw_text: str = ""

class QuantityParser:
    """Элемент-функция: Извлекает количество и цену за единицу."""
    
    def __init__(self, locale_config: Optional['LocaleConfig'] = None):
        """
        Args:
            locale_config: Конфигурация локали (опционально)
        """
        self.locale_config = locale_config
        
        # Получаем единицы измерения из locale_config
        if locale_config and locale_config.patterns and locale_config.patterns.quantity_units:
            units = "|".join(locale_config.patterns.quantity_units)
            self.qty_x_pattern = re.compile(
                rf'(\d+[\.,]\d{{2,3}})\s*(?:{units})?\s*[xх*]\s*(\d+[\.,]\d{{2}})', 
                re.IGNORECASE
            )
        else:
            # Fallback: базовые единицы
            self.qty_x_pattern = re.compile(
                r'(\d+[\.,]\d{2,3})\s*(?:kg|stk|шт)?\s*[xх*]\s*(\d+[\.,]\d{2})', 
                re.IGNORECASE
            )
        
        self.simple_qty_pattern = re.compile(r'(\d+)\s*[xх*]\s*(\d+[\.,]\d{2})', re.IGNORECASE)

    def parse(self, text: str) -> Optional[QtyResult]:
        """
        ЦКП: Объект QtyResult или None.
        """
        if not text:
            return None
            
        # Пробуем сложный паттерн (с весом)
        match = self.qty_x_pattern.search(text)
        if match:
            return QtyResult(
                qty=self._to_decimal(match.group(1)),
                unit_price=self._to_decimal(match.group(2)),
                raw_text=match.group(0)
            )
            
        # Пробуем простой паттерн (шт x цена)
        match = self.simple_qty_pattern.search(text)
        if match:
            return QtyResult(
                qty=Decimal(match.group(1)),
                unit_price=self._to_decimal(match.group(2)),
                raw_text=match.group(0)
            )
            
        return None

    def _to_decimal(self, val: str) -> Decimal:
        return Decimal(val.replace(',', '.'))



