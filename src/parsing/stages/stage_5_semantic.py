"""
Stage 5: Semantic Extraction

ЦКП: Извлечение товаров из чека.

Входные данные: LayoutResult, LocaleResult, StoreResult, MetadataResult
Выходные данные: SemanticResult (список ParsedItem)

Алгоритм:
1. Классификация строк (ITEM, HEADER, FOOTER, TOTAL, DISCOUNT)
2. Парсинг строк-товаров (name, quantity, price, total)
3. Обработка скидок и многострочных товаров

Архитектурный принцип:
- Конфигурация (ключевые слова, паттерны) загружается из YAML
- Логика (обработка, фильтрация) в коде
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .stage_1_layout import LayoutResult, Line
from .stage_2_locale import LocaleResult
from .stage_3_store import StoreResult
from .stage_4_metadata import MetadataResult
from ..locales.config_loader import ConfigLoader, ParsingConfig


@dataclass
class ParsedItem:
    """
    Товар извлечённый из чека.
    
    Минимальный набор полей для D2->D3.
    """
    name: str                                   # Название товара
    quantity: Optional[float] = None            # Количество
    price: Optional[float] = None               # Цена за единицу
    total: Optional[float] = None               # Итого за позицию
    is_discount: bool = False                   # Это скидка?
    is_pfand: bool = False                      # Это Pfand (залог)?
    line_number: int = 0                        # Номер строки
    raw_text: str = ""                          # Исходный текст строки
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price,
            "total": self.total,
            "is_discount": self.is_discount,
            "is_pfand": self.is_pfand,
            "line_number": self.line_number,
            "raw_text": self.raw_text,
        }


@dataclass
class SemanticResult:
    """
    Результат Stage 5: Semantic Extraction.
    
    ЦКП: Список извлечённых товаров.
    """
    items: List[ParsedItem] = field(default_factory=list)
    discounts: List[ParsedItem] = field(default_factory=list)
    skipped_lines: int = 0
    parsed_lines: int = 0
    
    @property
    def items_total(self) -> float:
        """Сумма всех товаров."""
        return sum(item.total or 0 for item in self.items if not item.is_discount)
    
    @property
    def discounts_total(self) -> float:
        """Сумма всех скидок."""
        return sum(abs(item.total or 0) for item in self.discounts)
    
    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "discounts": [item.to_dict() for item in self.discounts],
            "items_count": len(self.items),
            "discounts_count": len(self.discounts),
            "items_total": self.items_total,
            "discounts_total": self.discounts_total,
            "skipped_lines": self.skipped_lines,
            "parsed_lines": self.parsed_lines,
        }


class SemanticStage:
    """
    Stage 5: Semantic Extraction.
    
    ЦКП: Извлечение товаров из строк чека.
    """
    
    def __init__(
        self,
        config_loader: Optional[ConfigLoader] = None,
    ):
        """
        Args:
            config_loader: Загрузчик конфигов локалей
        """
        if config_loader is None:
            # Default: создаём локальный загрузчик
            from ..locales.config_loader import ConfigLoader
            config_loader = ConfigLoader()
        
        self.config_loader = config_loader
    
    def process(
        self,
        layout: LayoutResult,
        locale: LocaleResult,
        store: StoreResult,
        metadata: MetadataResult,
    ) -> SemanticResult:
        """
        Извлекает товары из чека.
        
        Args:
            layout: Результат Stage 1
            locale: Результат Stage 2
            store: Результат Stage 3
            metadata: Результат Stage 4
            
        Returns:
            SemanticResult: Извлечённые товары
        """
        logger.debug(f"[Stage 5: Semantic] Обработка {len(layout.lines)} строк")
        
        # Загружаем конфигурацию локали
        config = self.config_loader.load(locale.locale_code)
        
        items: List[ParsedItem] = []
        discounts: List[ParsedItem] = []
        skipped = 0
        parsed = 0
        
        # Определяем границы области товаров
        # (пропускаем заголовок и футер)
        start_line = self._find_items_start(layout, store)
        end_line = self._find_items_end(layout, metadata)
        
        logger.debug(f"[Stage 5: Semantic] Область товаров: строки {start_line}-{end_line}")
        
        for i, line in enumerate(layout.lines):
            # Пропускаем заголовок и футер
            if i < start_line or i > end_line:
                skipped += 1
                continue
            
            # Пропускаем служебные строки
            if self._should_skip_line(line.text, config):
                skipped += 1
                continue
            
            # Парсим строку
            item = self._parse_item_line(line, config)
            
            if item:
                parsed += 1
                
                if item.is_discount:
                    discounts.append(item)
                else:
                    items.append(item)
            else:
                skipped += 1
        
        result = SemanticResult(
            items=items,
            discounts=discounts,
            skipped_lines=skipped,
            parsed_lines=parsed,
        )
        
        logger.info(
            f"[Stage 5: Semantic] Результат: {len(items)} товаров, "
            f"{len(discounts)} скидок, {skipped} пропущено"
        )
        
        return result
    
    def _find_items_start(self, layout: LayoutResult, store: StoreResult) -> int:
        """Находит начало области товаров."""
        # После названия магазина + несколько строк
        if store.matched_in_line >= 0:
            return min(store.matched_in_line + 3, len(layout.lines) - 1)
        return 3  # По умолчанию с 4-й строки
    
    def _find_items_end(self, layout: LayoutResult, metadata: MetadataResult) -> int:
        """Находит конец области товаров."""
        # До строки с итогом
        if metadata.total_line_number >= 0:
            return max(0, metadata.total_line_number - 1)
        # По умолчанию до последних 5 строк
        return max(0, len(layout.lines) - 5)
    
    def _should_skip_line(self, text: str, config: ParsingConfig) -> bool:
        """
        Проверяет, нужно ли пропустить строку.
        
        Args:
            text: Текст строки
            config: Конфигурация локали (ключевые слова, паттерны)
        """
        text_lower = text.lower()
        
        # Слишком короткая
        if len(text.strip()) < 3:
            return True
        
        # Проверяем skip-слова из конфига
        for keyword in config.skip_keywords:
            if keyword in text_lower:
                logger.debug(f"[Stage 5] Skip по ключевому слову: '{text}' ({keyword})")
                return True
        
        # Проверяем паттерны веса из конфига
        for pattern in config.weight_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                logger.debug(f"[Stage 5] Skip по паттерну веса: '{text}'")
                return True
        
        # Проверяем паттерны налогов из конфига
        for pattern in config.tax_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                logger.debug(f"[Stage 5] Skip по паттерну налога: '{text}'")
                return True
        
        return False
    
    def _parse_item_line(self, line: Line, config: ParsingConfig) -> Optional[ParsedItem]:
        """
        Парсит строку как товар.
        
        Args:
            line: Строка для парсинга
            config: Конфигурация локали (ключевые слова скидок)
        """
        text = line.text.strip()
        
        # Проверяем на скидку (из конфига)
        is_discount = self._is_discount_line(text, config.discount_keywords)
        
        # Проверяем на Pfand
        is_pfand = "pfand" in text.lower() or "leergut" in text.lower()
        
        # Извлекаем компоненты
        name, quantity, price, total = self._extract_item_components(text)
        
        # Если не удалось извлечь имя или цену — пропускаем
        if not name or (total is None and price is None):
            return None
        
        return ParsedItem(
            name=name,
            quantity=quantity,
            price=price,
            total=total,
            is_discount=is_discount,
            is_pfand=is_pfand,
            line_number=line.line_number,
            raw_text=text,
        )
    
    def _is_discount_line(self, text: str, discount_keywords: List[str]) -> bool:
        """
        Проверяет, является ли строка скидкой.
        
        Args:
            text: Текст строки
            discount_keywords: Ключевые слова скидок из конфига
        """
        text_lower = text.lower()
        
        # Проверяем ключевые слова скидок
        for keyword in discount_keywords:
            if keyword in text_lower:
                return True
        
        # Отрицательная цена (минус в конце строки)
        if re.search(r"-\s*\d+[,\.]\d{2}\s*$", text):
            return True
        
        return False
    
    def _extract_item_components(
        self, text: str
    ) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
        """
        Извлекает компоненты товара из строки.
        
        Returns:
            (name, quantity, price, total)
        
        Паттерн: НАЗВАНИЕ [QTY x PRICE] TOTAL
        Примеры:
        "Milch 3.5% 1,29 A"
        "Brot 2 x 0,99 1,98 B"
        "JOGURT GRECKI 3,49"
        """
        # Определяем десятичный разделитель (по умолчанию — европейский)
        decimal_sep = ","
        
        # Находим все числа в строке
        if decimal_sep == ",":
            price_pattern = r"(\d+),(\d{2})"
        else:
            price_pattern = r"(\d+)\.(\d{2})"
        
        prices = re.findall(price_pattern, text)
        
        if not prices:
            return None, None, None
        
        # Последняя цена — это total
        total_match = prices[-1]
        total = float(f"{total_match[0]}.{total_match[1]}")
        
        # Убираем цены из текста, чтобы получить название
        name = text
        for p in prices:
            price_str = f"{p[0]}{decimal_sep}{p[1]}"
            name = name.replace(price_str, "")
        
        # Очищаем название
        name = self._clean_item_name(name)
        
        if not name:
            return None, None, None
        
        # Ищем количество (например, "2 x" или "2x" или "2 St")
        quantity = None
        price = None
        
        # Паттерн: целое число + x + пробел/число
        # НЕ захватывает числа из цен (например, "4,29 x 2" — это 2, а не 4,29)
        qty_match = re.search(r"(?:^|\s)(\d{1,3})\s*[xX×]\s*(?:\d|$)", text)
        if qty_match:
            quantity = float(qty_match.group(1))
            # Если есть quantity и несколько цен, первая — unit price
            if len(prices) >= 2:
                price_match = prices[0]
                price = float(f"{price_match[0]}.{price_match[1]}")
        
        return name, quantity, price, total
    
    def _clean_item_name(self, name: str) -> str:
        """Очищает название товара."""
        # Убираем лишние символы
        name = re.sub(r"[xX×]\s*$", "", name)  # "2 x" в конце
        name = re.sub(r"\s+", " ", name)       # Множественные пробелы
        name = re.sub(r"^[\s\-\*]+", "", name)  # Ведущие символы
        name = re.sub(r"[\s\-\*]+$", "", name)  # Концевые символы
        
        # Убираем tax class (A, B, C в конце)
        name = re.sub(r"\s+[A-C]\s*$", "", name)
        
        return name.strip()
