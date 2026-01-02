"""
Line Classifier - Классификация строк чека.

ЦКП: Определение типа строки (товар / служебная / header / footer) и границ товарной зоны.

SRP: Только классификация строк, без парсинга товаров.
"""

import re
from typing import Tuple
from loguru import logger

from ..s3_layout.stage import LayoutResult, Line
from ..s5_store_detection.stage import StoreResult
from ..s6_metadata.stage import MetadataResult
from ..locales.config_loader import SemanticConfig


class LineClassifier:
    """
    Классификатор строк чека.
    
    ЦКП: Определение типа строки и границ товарной зоны.
    """
    
    def should_skip(self, text: str, config: SemanticConfig) -> bool:
        """
        Определяет, нужно ли пропустить строку (служебная/техническая).
        
        Args:
            text: Текст строки
            config: Конфигурация семантики
            
        Returns:
            True если строку нужно пропустить
        """
        text_lower = text.lower()
        
        # Пустые или очень короткие строки
        if len(text.strip()) < 2:
            return True
        
        # Проверка по skip_keywords из конфига
        for keyword in config.skip_keywords:
            if keyword in text_lower:
                return True
        
        # Проверка по weight_patterns (весовые товары)
        for pattern in config.weight_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Проверка по tax_patterns (налоговые строки)
        for pattern in config.tax_patterns:
            if re.search(pattern, text.strip(), re.IGNORECASE):
                return True
        
        return False
    
    def is_header_line(
        self, 
        line: Line, 
        layout: LayoutResult, 
        config: SemanticConfig
    ) -> bool:
        """
        Проверка на заголовочную строку (Header Protector).
        
        Заголовки обычно в верхней трети чека и содержат юридические идентификаторы.
        
        Args:
            line: Проверяемая строка
            layout: Результат Layout stage
            config: Конфигурация семантики
            
        Returns:
            True если строка является заголовком
        """
        # Проверка позиции (верхняя треть чека)
        if line.y_position >= layout.image_height / 3:
            return False
        
        # Проверка по legal_header_identifiers из конфига
        for identifier in config.legal_header_identifiers:
            if identifier.lower() in line.text.lower():
                logger.debug(f"[LineClassifier] Header detected: '{line.text}' (identifier: '{identifier}')")
                return True
        
        return False
    
    def is_footer_line(
        self, 
        line: Line, 
        line_idx: int, 
        metadata: MetadataResult
    ) -> bool:
        """
        Проверка на футер (Footer Protector).
        
        Футер - строки после итоговой суммы, содержащие налоговую информацию.
        
        Args:
            line: Проверяемая строка
            line_idx: Индекс строки
            metadata: Результат Metadata stage
            
        Returns:
            True если строка является футером
        """
        # Если итоговая сумма не найдена, не можем определить футер
        if metadata.total_line_number == -1:
            return False
        
        # Футер начинается после строки с итоговой суммой
        if line_idx <= metadata.total_line_number:
            return False
        
        # Проверка на налоговые ключевые слова
        footer_keywords = ['steuer', 'mwst', 'vat', 'ptu', 'netto', 'brutto']
        line_lower = line.text.lower()
        
        if any(kw in line_lower for kw in footer_keywords):
            logger.debug(f"[LineClassifier] Footer detected: '{line.text}' (line {line_idx})")
            return True
        
        # Если строка далеко после итога (больше 1 строки) - тоже футер
        if line_idx > metadata.total_line_number + 1:
            return True
        
        return False
    
    def find_items_zone(
        self, 
        layout: LayoutResult, 
        store: StoreResult, 
        metadata: MetadataResult
    ) -> Tuple[int, int]:
        """
        Определяет границы товарной зоны (start_line, end_line).
        
        Товарная зона:
        - Начинается после названия магазина (store.matched_in_line + 2)
        - Заканчивается перед итоговой суммой (metadata.total_line_number - 1)
        
        Args:
            layout: Результат Layout stage
            store: Результат Store stage
            metadata: Результат Metadata stage
            
        Returns:
            (start_line, end_line) - границы товарной зоны
        """
        # Начало: после названия магазина
        if store.matched_in_line >= 0:
            start_line = min(store.matched_in_line + 2, len(layout.lines) - 1)
        else:
            start_line = 2  # По умолчанию со 2-й строки
        
        # Конец: перед итоговой суммой
        if metadata.total_line_number >= 0:
            end_line = max(0, metadata.total_line_number - 1)
        else:
            # Fallback: последние 5 строк не товары
            end_line = max(0, len(layout.lines) - 5)
        
        return start_line, end_line
