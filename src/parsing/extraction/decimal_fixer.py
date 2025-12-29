import re
from typing import Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class DecimalFixResult:
    text: str
    was_fixed: bool
    count: int

class DecimalFixer:
    """
    Элемент-функция: Исправляет точку на запятую в ценах (для европейских чеков).
    
    Вектор: Перенос логики из Legacy E5 Decimal Fix.
    ЦКП: Исправленная строка текста + флаг фиксации.
    """
    
    def __init__(self):
        # Паттерн для цены с точкой вместо запятой
        # Ищем: число.число где число после точки 2 цифры (типичная цена)
        # Привязка к маркеру налога (A, B, M) или концу строки
        self.price_dot_pattern = re.compile(r"(\d+)\.(\d{2})(?=\s*[ABM]?\s*$|\s+[ABM]\s|\s+EUR|\s+-)")
        self.date_pattern = re.compile(r"\d{2}\.\d{2}\.\d{2,4}|\d{4}\.\d{2}\.\d{2}")

    def fix(self, text: str) -> DecimalFixResult:
        """
        ЦКП: Результат исправления (DecimalFixResult).
        """
        if not text:
            return DecimalFixResult(text=text, was_fixed=False, count=0)
            
        # 1. Защита от дат
        if self.date_pattern.search(text):
            return DecimalFixResult(text=text, was_fixed=False, count=0)
            
        fixes_count = 0
        
        def replace_dot(match):
            nonlocal fixes_count
            fixes_count += 1
            return f"{match.group(1)},{match.group(2)}"

        fixed_text = self.price_dot_pattern.sub(replace_dot, text)
        
        was_fixed = fixes_count > 0
        if was_fixed:
            logger.debug(f"[DecimalFixer] Исправлено: '{text}' -> '{fixed_text}'")
            
        return DecimalFixResult(
            text=fixed_text,
            was_fixed=was_fixed,
            count=fixes_count
        )



