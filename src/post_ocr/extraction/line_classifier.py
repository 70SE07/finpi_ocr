from enum import Enum
from typing import Optional, List
import re

class LineType(Enum):
    ITEM = "item"
    TOTAL = "total"
    DISCOUNT = "discount"
    TAX_INFO = "tax_info"
    NOISE = "noise"

class LineClassifier:
    """Элемент-функция: Определяет тип строки чека."""
    
    def __init__(self):
        self.total_keywords = ["gesamtbetrag", "summe", "total", "zu zahlen", "belegsumme"]
        self.discount_keywords = ["preisvorteil", "rabatt", "nachlass", "aktionsnachlass", "coupon"]
        self.noise_keywords = ["tel.", "fax.", "obj.-nr.", "terminal", "beleg-nr.", "datum", "uhrzeit"]

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
