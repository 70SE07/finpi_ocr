import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class QtyResult:
    qty: Decimal
    unit_price: Optional[Decimal] = None
    raw_text: str = ""

class QuantityParser:
    """Элемент-функция: Извлекает количество и цену за единицу."""
    
    def __init__(self):
        # Паттерн: 1,207 kg x 8,99
        self.qty_x_pattern = re.compile(r'(\d+[\.,]\d{2,3})\s*(?:kg|stk|шт)?\s*[xх*]\s*(\d+[\.,]\d{2})', re.IGNORECASE)
        # Паттерн: 2 x 0,99
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



