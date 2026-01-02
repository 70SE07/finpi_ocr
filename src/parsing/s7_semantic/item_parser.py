"""
Item Parser - Парсинг товарных строк.

ЦКП: Преобразование строки чека в товар(ы) с названием, количеством, ценой.

SRP: Только парсинг товаров, без классификации строк и валидации цен.
"""

import re
from typing import List, Optional, Tuple
from loguru import logger

from ..s3_layout.stage import Line
from ..locales.config_loader import SemanticConfig
from contracts.d1_extraction_dto import Word

from .price_extractor import PriceExtractor
from .discount_handler import DiscountHandler


class ItemParser:
    """
    Парсер товарных строк.
    
    ЦКП: Распарсенные товары из строки чека.
    """
    
    def __init__(self, price_extractor: PriceExtractor, discount_handler: DiscountHandler):
        """
        Args:
            price_extractor: Экстрактор цен
            discount_handler: Обработчик скидок
        """
        self.price_extractor = price_extractor
        self.discount_handler = discount_handler
    
    def parse(self, line: Line, config: SemanticConfig) -> List["ParsedItem"]:
        """
        Парсит строку и возвращает список товаров.
        
        Args:
            line: Строка чека
            config: Конфигурация семантики
            
        Returns:
            Список распарсенных товаров
        """
        # Импортируем ParsedItem здесь, чтобы избежать циклических импортов
        from .stage import ParsedItem
        
        text = line.text
        
        # Извлекаем все цены
        price_strings = self.price_extractor.extract_strings(text, allow_joined=config.allow_joined_prices)
        prices = self.price_extractor.extract_all(text, allow_joined=config.allow_joined_prices)
        
        # Если несколько цен - пробуем разделить строку
        if len(prices) >= 2:
            split_items = self._try_split_multi_item_line(text, prices, price_strings, line, config)
            if split_items:
                return split_items
        
        # Обычный парсинг одной строки
        name, quantity, price, total = self.extract_components(text, config)
        
        if total is not None:
            # Определяем, является ли это скидкой
            is_discount = self.discount_handler.is_discount(name or text, config.discount_keywords)
            is_pfand = self.discount_handler.is_pfand(name or text)
            
            return [ParsedItem(
                name=name or "",
                quantity=quantity,
                price=price,
                total=total,
                is_discount=is_discount,
                is_pfand=is_pfand,
                line_number=line.line_number,
                raw_text=text
            )]
        
        return []
    
    def _try_split_multi_item_line(
        self,
        text: str,
        prices: List[float],
        price_strings: List[str],
        line: Line,
        config: SemanticConfig
    ) -> Optional[List["ParsedItem"]]:
        """
        Пытается разделить строку с несколькими товарами.
        
        Args:
            text: Текст строки
            prices: Список найденных цен
            price_strings: Список строк цен
            line: Исходная строка
            config: Конфигурация
            
        Returns:
            Список товаров или None если разделение не удалось
        """
        from .stage import ParsedItem
        
        # Проверка на явный маркер умножения
        has_explicit_multi = bool(re.search(r"(\*|[\s*x×X]\s+)", text.upper())) or \
                           any(op in text.upper() for op in [' VAT ', ' IVA ', ' PTU '])
        
        # Проверка на паттерн весового товара
        weight_pattern = self.price_extractor.detect_weight_pattern(prices)
        if weight_pattern:
            # Это весовой товар, не разделяем
            return None
        
        # Решение о разделении
        should_split = False
        if not has_explicit_multi and len(prices) >= 2:
            should_split = True
        elif has_explicit_multi and len(prices) >= 4:
            should_split = True
        
        if not should_split:
            return None
        
        # Разделяем по последней цене
        last_price_match = list(re.finditer(r"(?<![\d.,])\-?\d+[.,]\d{2}(?![\d.,])", text))[-1]
        pos = last_price_match.start()
        
        part1, part2 = text[:pos].strip(), text[pos:].strip()
        logger.debug(f"[ItemParser] Multi-Price Split: '{part1}' | '{part2}'")
        
        # Рекурсивно парсим обе части
        line1 = Line(text=part1, words=[], y_position=line.y_position, line_number=line.line_number)
        line2 = Line(text=part2, words=[], y_position=line.y_position, line_number=line.line_number)
        
        res1 = self.parse(line1, config)
        res2 = self.parse(line2, config)
        
        if res1 and res2:
            return res1 + res2
        
        return None
    
    def extract_components(
        self, 
        text: str, 
        config: SemanticConfig
    ) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
        """
        Извлекает компоненты товара: name, quantity, price, total.
        
        Args:
            text: Текст строки
            config: Конфигурация семантики
            
        Returns:
            (name, quantity, price, total) - компоненты товара
        """
        # Извлекаем цены
        prices = self.price_extractor.extract_all(text, allow_joined=config.allow_joined_prices)
        
        if not prices:
            return None, None, None, None
        
        # Последняя цена - это total
        total = prices[-1]
        
        # Удаляем цены из текста, чтобы получить название
        name = text
        price_strings = self.price_extractor.extract_strings(text, allow_joined=config.allow_joined_prices)
        for price_str in price_strings:
            name = name.replace(price_str, "").strip()
        
        # Очищаем название
        name = self.clean_name(name)
        
        quantity, price = None, None
        
        # Паттерн 1: Явный маркер умножения (1*5.99, 0.5 x 9.99)
        qty_pattern = r"(?:^|\s)(\d{1,3}(?:[.,]\d{1,3})?)\s*[xX×*]\s*(?:\d|$)"
        qty_match = re.search(qty_pattern, text)
        if qty_match:
            try:
                quantity = float(qty_match.group(1).replace(",", "."))
                if len(prices) >= 2:
                    price = prices[0]  # Первая цена - это unit price
            except (ValueError, IndexError):
                pass
        
        # Паттерн 2: Весовой товар без маркера (qty price total)
        if quantity is None and len(prices) == 3:
            weight_pattern = self.price_extractor.detect_weight_pattern(prices)
            if weight_pattern:
                qty, unit_price, total_price = weight_pattern
                quantity = qty
                price = unit_price
                total = total_price
                logger.debug(f"[ItemParser] Weight item: qty={quantity}, price={price}, total={total}")
        
        return name, quantity, price, total
    
    def clean_name(self, name: str) -> str:
        """
        Очищает название товара от артефактов.
        
        Args:
            name: Сырое название
            
        Returns:
            Очищенное название
        """
        # Убираем маркеры умножения в конце
        name = re.sub(r"[xX×]\s*$", "", name)
        
        # Нормализуем пробелы
        name = re.sub(r"\s+", " ", name)
        
        # Убираем лишние символы в начале/конце
        name = re.sub(r"^[\s\-\*]+", "", name)
        name = re.sub(r"[\s\-\*]+$", "", name).strip()
        
        # Убираем одиночные буквы налогов в конце (например, "A", "B", "C")
        name = re.sub(r"\s+[A-Z]\s*$", "", name)
        
        return name
    
    def split_by_geometry(self, line: Line, threshold: int) -> List[Line]:
        """
        Геометрическое разделение строки по Y-координатам слов.
        
        Если слова в строке имеют разные Y-координаты (больше threshold),
        разделяет строку на несколько подстрок.
        
        Args:
            line: Исходная строка
            threshold: Порог разницы Y для разделения
            
        Returns:
            Список разделенных строк
        """
        if not line.words or len(line.words) < 2:
            return [line]
        
        # Сортируем слова по Y
        sorted_words = sorted(line.words, key=lambda w: w.bounding_box.y)
        
        # Группируем слова по Y (кластеры)
        clusters = []
        current_cluster = [sorted_words[0]]
        
        for i in range(1, len(sorted_words)):
            w = sorted_words[i]
            prev_w = current_cluster[-1]
            
            # Если разница Y больше threshold - новый кластер
            if abs(w.bounding_box.y - prev_w.bounding_box.y) > threshold:
                clusters.append(current_cluster)
                current_cluster = [w]
            else:
                current_cluster.append(w)
        
        clusters.append(current_cluster)
        
        # Если только один кластер - не разделяем
        if len(clusters) == 1:
            return [line]
        
        # Создаем новые строки из кластеров
        new_lines = []
        for cluster in clusters:
            # Сортируем слова в кластере по X
            sorted_cluster = sorted(cluster, key=lambda w: w.bounding_box.x)
            
            # Собираем текст
            text = " ".join([w.text for w in sorted_cluster])
            
            # Создаем новую Line
            new_line = Line(
                text=text,
                words=sorted_cluster,
                y_position=min(w.bounding_box.y for w in cluster),
                x_min=min(w.bounding_box.x for w in cluster),
                x_max=max(w.bounding_box.x + w.bounding_box.width for w in cluster),
                confidence=sum(w.confidence for w in cluster) / len(cluster),
                line_number=line.line_number
            )
            new_lines.append(new_line)
        
        return new_lines
