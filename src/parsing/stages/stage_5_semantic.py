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
from ..locales.config_loader import ConfigLoader, SemanticConfig, LocaleConfig


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
    
    Загружает конфигурацию локали (ключевые слова, паттерны для фильтрации).
    """
    
    def __init__(
        self,
        config_loader: Optional[ConfigLoader] = None,
        config: Optional[LocaleConfig] = None,
    ):
        """
        Args:
            config_loader: DI для загрузки конфигов (для мульти-локальной поддержки)
            config: Статическая конфигурация (legacy/testing)
        """
        self.config_loader = config_loader or ConfigLoader()
        # Если передан статический конфиг, используем его как кэш/дефолт
        self.config = config
    
    @staticmethod
    def _empty_metadata_config() -> "MetadataConfig":
        """Создаёт пустую конфигурацию метаданных."""
        from ..locales.locale_config import MetadataConfig
        return MetadataConfig(total_keywords=[])
    
    @staticmethod
    def _empty_semantic_config() -> "SemanticConfig":
        """Создаёт пустую конфигурацию семантического этапа."""
        from ..locales.locale_config import SemanticConfig
        return SemanticConfig(
            skip_keywords=[],
            discount_keywords=[],
            weight_patterns=[],
            tax_patterns=[],
        )
    
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
        
        # Получаем конфигурацию семантики из LocaleConfig
        if self.config:
             # Legacy/Testing: используем статическую
             semantic_config = self.config.semantic
        else:
             # Production: загружаем динамически по локали
             try:
                 full_config = self.config_loader.load(locale.locale_code)
                 semantic_config = full_config.semantic
             except Exception as e:
                 logger.warning(f"[SemanticStage] Ошибка загрузки конфига для {locale.locale_code}: {e}")
                 semantic_config = self._empty_semantic_config()
        
        items: List[ParsedItem] = []
        discounts: List[ParsedItem] = []
        skipped = 0
        parsed = 0
        
        # Определяем границы области товаров
        start_line = self._find_items_start(layout, store)
        end_line = self._find_items_end(layout, metadata)
        
        logger.debug(f"[Stage 5: Semantic] Область товаров: строки {start_line}-{end_line}")
        
        for i, line in enumerate(layout.lines):
            # Пропускаем заголовок и футер
            if i < start_line or i > end_line:
                skipped += 1
                continue
            
            # Пропускаем служебные строки (из конфига)
            if self._should_skip_line(line.text, semantic_config):
                skipped += 1
                continue
            
            # Парсим строку (может быть несколько товаров в одной склеенной строке)
            line_items = self._parse_item_line(line, semantic_config)
            
            if line_items:
                for item in line_items:
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
    
    def _should_skip_line(self, text: str, config: "SemanticConfig") -> bool:
        """
        Проверяет, нужно ли пропустить строку.
        
        Args:
            text: Текст строки
            config: Конфигурация локали (из LocaleConfig.semantic)
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
    
    def _parse_item_line(self, line: Line, config: SemanticConfig) -> List[ParsedItem]:
        """
        Парсит строку чека. Пытается найти один или несколько товаров.
        
        Args:
            line: Строка из LayoutStage
            config: Конфигурация локали
            
        Returns:
            List[ParsedItem]: Список найденных товаров
        """
        text = line.text
        
        # 1. Пробуем распарсить строку целиком
        name, quantity, price, total = self._extract_item_components(text)
        
        if not name or total is None:
            return []
            
        # 2. Проверка на "склеенную" строку (несколько цен total в одной строке)
        # Если в строке 3+ цены и есть разделители типа '=', 
        # возможно это склейка типа "Item1 1.23 = 1.23 Item2 4.56 = 4.56"
        price_pattern = r"(?<![\d.,])(-?\d+)[.,](\d{2})(?![\d.,])"
        all_prices = list(re.finditer(price_pattern, text))
        
        # Если цен много (например, 4), и они разделены текстом
        if len(all_prices) >= 3:
            # Ищем разрыв: если после цены идет много текста и НОВАЯ цена
            # В PL_001: "... 14.99 C CHC MANDARYNKI ..."
            # Мы можем попробовать разделить строку по последней цене первого товара
            # Но это сложно. Проще: если нашли явный разделитель товаров.
            pass

        # Для PL_001 специфично: "TOTAL C NAME2"
        # Попробуем разделить по паттерну [PRICE] [A-C] [NAME]
        split_pattern = r"((?<![\d.,])\-?\d+[.,]\d{2}(?![\d.,])\s+[A-Z]\s+)([A-Z]{3,})"
        match = re.search(split_pattern, text)
        if match:
            # Разделяем на две части
            pos = match.start(2)
            part1 = text[:pos]
            part2 = text[pos:]
            
            logger.debug(f"[Stage 5] Semantic Split: '{part1}' | '{part2}'")
            
            item1_comps = self._extract_item_components(part1)
            item2_comps = self._extract_item_components(part2)
            
            results = []
            if item1_comps[0] and item1_comps[3] is not None:
                results.append(self._create_item(item1_comps, line.line_number, config))
            if item2_comps[0] and item2_comps[3] is not None:
                # Рекурсивно проверяем вторую часть (вдруг там 3 товара)
                # Создаем временную линию
                temp_line = Line(
                    text=part2, 
                    line_number=line.line_number,
                    words_count=0,
                    confidence=line.confidence,
                    y_position=line.y_position,
                    x_min=line.x_min,
                    x_max=line.x_max
                )
                results.extend(self._parse_item_line(temp_line, config))
            
            if results:
                return results

        # Если не разделили, возвращаем один товар
        return [self._create_item((name, quantity, price, total), line.line_number, config)]

    def _create_item(self, components: Tuple, line_number: int, config: SemanticConfig) -> ParsedItem:
        """Вспомогательный метод для создания ParsedItem из компонентов."""
        name, quantity, price, total = components
        is_discount = self._is_discount_line(name, config.discount_keywords)
        
        return ParsedItem(
            name=name,
            quantity=quantity,
            price=price,
            total=total,
            is_discount=is_discount,
            line_number=line_number,
            raw_text=name # Временно, потом обновим если надо
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
        "Apple 0.694 * 2.99"
        """
        # 1. Поиск цен (поддерживаем и точку, и запятую, так как OCR может путать их)
        # Ищем числа с 2 знаками после разделителя, опционально с минусом в начале (-3.33)
        # Используем lookbehind/lookahead чтобы не цеплять части дат (10.08.2025) или весов (1.398)
        price_pattern = r"(?<![\d.,])(-?\d+)[.,](\d{2})(?![\d.,])"
        prices = re.findall(price_pattern, text)
        
        if not prices:
            return None, None, None, None
        
        # Последняя цена — это total
        total_match = prices[-1]
        # Нормализуем в float (всегда через точку)
        total = float(f"{total_match[0]}.{total_match[1]}")
        
        # Убираем цены из текста, чтобы получить название
        name = text
        for p in prices:
            # Пытаемся удалить оба варианта (с точкой и запятой), чтобы очистить строку
            name = name.replace(f"{p[0]},{p[1]}", "").replace(f"{p[0]}.{p[1]}", "")
        
        # Очищаем название
        name = self._clean_item_name(name)
        
        if not name:
            return None, None, None, None
        
        # 2. Поиск количества
        # Поддерживаем:
        # - Целые (2) и дробные (0.694, 1,5)
        # - Разделители: x, X, ×, *
        quantity = None
        price = None
        
        # Паттерн: (число) [x*] (число/цена)
        # Группа 1: Количество (до 3 цифр до точки/запятой, опционально дробная часть)
        qty_pattern = r"(?:^|\s)(\d{1,3}(?:[.,]\d{1,3})?)\s*[xX×*]\s*(?:\d|$)"
        qty_match = re.search(qty_pattern, text)
        
        if qty_match:
            qty_str = qty_match.group(1).replace(",", ".")
            try:
                quantity = float(qty_str)
            except ValueError:
                pass # Если не удалось распарсить, оставляем None
                
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
