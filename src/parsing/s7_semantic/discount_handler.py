"""
Discount Handler - Обработка скидок и залогов.

ЦКП: Определение скидок и залогов (Pfand) в строках чека.

SRP: Только классификация скидок/залогов, без парсинга цен.
"""

import re
from typing import List
from loguru import logger


class DiscountHandler:
    """
    Обработка скидок и залогов.
    
    ЦКП: Корректная классификация скидок и залогов.
    """
    
    # Ключевые слова для залогов (Pfand/Leergut)
    PFAND_KEYWORDS = ["pfand", "leergut"]
    
    def is_discount(self, text: str, discount_keywords: List[str]) -> bool:
        """
        Определяет, является ли строка скидкой.
        
        Args:
            text: Текст строки
            discount_keywords: Список ключевых слов для скидок (из конфига)
            
        Returns:
            True если строка является скидкой
        """
        text_lower = text.lower()
        
        # Залог (Pfand) - это НЕ скидка
        if self.is_pfand(text):
            return False
        
        # Проверка по ключевым словам из конфига
        if any(kw in text_lower for kw in discount_keywords):
            return True
        
        # Проверка на отрицательную цену в конце строки
        if self.has_negative_price(text):
            return True
        
        return False
    
    def is_pfand(self, text: str) -> bool:
        """
        Определяет, является ли строка залогом (Pfand/Leergut).
        
        Args:
            text: Текст строки
            
        Returns:
            True если строка является залогом
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.PFAND_KEYWORDS)
    
    def has_negative_price(self, text: str) -> bool:
        """
        Проверка на отрицательную цену в конце строки.
        
        Паттерн: "- 12,34" или "-12.34" в конце строки.
        
        Args:
            text: Текст строки
            
        Returns:
            True если найдена отрицательная цена в конце
        """
        # Паттерн: минус, пробелы (опционально), число с запятой/точкой, конец строки
        pattern = r"-\s*\d+[,\.]\d{2}\s*$"
        return bool(re.search(pattern, text))
