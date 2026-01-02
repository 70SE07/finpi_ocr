"""
Price Extractor - Извлечение и валидация цен.

ЦКП: Извлечение цен из текста и Price Sanity Check.

SRP: Только работа с ценами (извлечение, валидация, очистка аномалий).
"""

import re
from typing import List, Optional, Tuple
from loguru import logger


class PriceExtractor:
    """
    Извлечение и валидация цен.
    
    ЦКП: Корректные цены без аномалий.
    """
    
    # Паттерн для извлечения цен (стандартный)
    STANDARD_PATTERN = r"(?<![\d.,])(-?\d+)[.,](\d{2})(?=\s*($|[A-Z%€£$]|zł|Kč))"
    
    # Паттерн для извлечения цен (relaxed - для склеенных цен)
    RELAXED_PATTERN = r"(-?\d+)[.,](\d{2})(?=\s*($|[A-Z%€£$]|zł|Kč))"
    
    def extract_all(self, text: str, allow_joined: bool = False) -> List[float]:
        """
        Извлекает все цены из строки.
        
        Args:
            text: Текст строки
            allow_joined: Использовать relaxed паттерн для склеенных цен
            
        Returns:
            Список найденных цен (float)
        """
        pattern = self.RELAXED_PATTERN if allow_joined else self.STANDARD_PATTERN
        matches = re.findall(pattern, text)
        
        prices = []
        for match in matches:
            try:
                price = float(f"{match[0]}.{match[1]}")
                prices.append(price)
            except (ValueError, IndexError):
                continue
        
        return prices
    
    def extract_strings(self, text: str, allow_joined: bool = False) -> List[str]:
        """
        Извлекает цены как строки (для Smart Cleaner).
        
        Args:
            text: Текст строки
            allow_joined: Использовать relaxed паттерн
            
        Returns:
            Список строк цен (например, "12,34", "5.99")
        """
        pattern = r"(?<![\d.,])\-?\d+[.,]\d{2}(?![\d.,])" if not allow_joined else r"\-?\d+[.,]\d{2}"
        matches = re.findall(pattern, text)
        return matches
    
    def validate(
        self, 
        price: float, 
        receipt_total: float, 
        items_count: int
    ) -> Tuple[bool, Optional[float]]:
        """
        Price Sanity Check.
        
        Проверяет, является ли цена аномальной, и пытается её исправить.
        
        Args:
            price: Проверяемая цена
            receipt_total: Итоговая сумма чека
            items_count: Количество уже найденных товаров
            
        Returns:
            (is_valid, corrected_price) - если is_valid=False, цена аномальна
        """
        if receipt_total <= 0:
            return True, price  # Не можем валидировать без итога
        
        # Аномалия 1: Цена больше итога
        if price > receipt_total:
            return False, None
        
        # Аномалия 2: Адаптивный порог
        # Для маленьких чеков (< 20) порог не применяется
        if receipt_total < 20:
            return True, price
        
        # Для средних (< 50): порог 50%
        if receipt_total < 50:
            threshold = 0.5
        else:
            # Для больших: порог 40% (короткие) или 25% (длинные)
            threshold = 0.4 if items_count <= 5 else 0.25
        
        if price > receipt_total * threshold:
            return False, None
        
        return True, price
    
    def clean_outlier(
        self, 
        price_str: str, 
        receipt_total: float, 
        strategy: str = "deep_prefix"
    ) -> Optional[float]:
        """
        Smart Cleaner для аномальных цен.
        
        Пытается исправить цену, отсекая цифры слева (например: 923.39 -> 23.39 -> 3.39).
        
        Args:
            price_str: Строка цены (например, "923,39")
            receipt_total: Итоговая сумма чека
            strategy: Стратегия очистки (пока только "deep_prefix")
            
        Returns:
            Исправленная цена или None если не удалось исправить
        """
        if strategy != "deep_prefix":
            return None
        
        # Нормализуем (запятая -> точка)
        current_price_str = price_str.replace(',', '.')
        
        # Отсекаем цифры слева, пока цена не станет вменяемой
        while len(current_price_str) > 3:  # Минимум X.XX
            try:
                candidate_price = float(current_price_str)
                
                # Если цена стала <= итога и вменяемая - берем!
                threshold_multiplier = 0.5
                if 0 < candidate_price <= receipt_total * threshold_multiplier:
                    logger.debug(f"[PriceExtractor] Smart Cleaner: {price_str} -> {candidate_price}")
                    return candidate_price
            except ValueError:
                pass
            
            # Отсекаем одну цифру слева
            current_price_str = current_price_str[1:]
        
        return None
    
    def detect_weight_pattern(
        self, 
        prices: List[float]
    ) -> Optional[Tuple[float, float, float]]:
        """
        Детекция паттерна весового товара без знака умножения.
        
        Формат: "NAME qty price total" (польский Carrefour)
        Пример: "C_CYTRYNY LUZ 0,29 9,99 2,90 C"
        Где qty < 10, qty * price ≈ total (с погрешностью 0.02)
        
        Args:
            prices: Список из 3 цен [qty, unit_price, total]
            
        Returns:
            (qty, unit_price, total) если паттерн найден, иначе None
        """
        if len(prices) != 3:
            return None
        
        try:
            qty = prices[0]
            unit_price = prices[1]
            total = prices[2]
            
            # Проверка: qty < 10 (типичный вес), и qty * price ≈ total
            if qty < 10 and abs(qty * unit_price - total) < 0.02:
                logger.debug(f"[PriceExtractor] Weight Pattern: qty={qty}, price={unit_price}, total={total}")
                return (qty, unit_price, total)
        except (ValueError, IndexError):
            pass
        
        return None
