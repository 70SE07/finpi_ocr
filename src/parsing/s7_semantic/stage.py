"""
Stage 7: Semantic Extraction - Оркестратор

ЦКП: Извлечение товаров с учетом вертикального контекста (многострочность).

Input: LayoutResult, LocaleResult, StoreResult, MetadataResult
Output: SemanticResult (items, discounts)

Алгоритм:
1. Определение границ товарной зоны (line_classifier)
2. Классификация строк (line_classifier)
3. Парсинг компонентов (item_parser)
4. Валидация цен (price_extractor)
5. Определение скидок (discount_handler)
"""

from dataclasses import dataclass, field
from typing import List, Optional
from loguru import logger

from ..s3_layout.stage import LayoutResult, Line
from ..s4_locale_detection.stage import LocaleResult
from ..s5_store_detection.stage import StoreResult
from ..s6_metadata.stage import MetadataResult
from ..locales.config_loader import ConfigLoader, SemanticConfig, LocaleConfig

from .line_classifier import LineClassifier
from .price_extractor import PriceExtractor
from .item_parser import ItemParser
from .discount_handler import DiscountHandler


@dataclass
class ParsedItem:
    """Распарсенный товар."""
    name: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    total: Optional[float] = None
    is_discount: bool = False
    is_pfand: bool = False
    line_number: int = 0
    raw_text: str = ""
    
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
    Результат Stage 7: Semantic Extraction.
    
    ЦКП: Список распарсенных товаров и скидок.
    """
    items: List[ParsedItem] = field(default_factory=list)
    discounts: List[ParsedItem] = field(default_factory=list)
    skipped_lines: int = 0
    parsed_lines: int = 0
    
    @property
    def items_total(self) -> float:
        return sum(item.total or 0 for item in self.items if not item.is_discount)
    
    @property
    def discounts_total(self) -> float:
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
    Stage 7: Semantic Extraction - Оркестратор.
    
    ЦКП: Координация модулей для извлечения товаров.
    
    Использует:
    - LineClassifier: классификация строк и границы зоны
    - ItemParser: парсинг товаров
    - PriceExtractor: валидация цен
    - DiscountHandler: определение скидок
    """
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None, config: Optional[LocaleConfig] = None):
        """
        Args:
            config_loader: Загрузчик конфигураций
            config: Опциональная конфигурация (для тестов)
        """
        self.config_loader = config_loader or ConfigLoader()
        self.config = config
        
        # Инициализация модулей
        self.price_extractor = PriceExtractor()
        self.discount_handler = DiscountHandler()
        self.line_classifier = LineClassifier()
        self.item_parser = ItemParser(self.price_extractor, self.discount_handler)
    
    def _empty_semantic_config(self) -> SemanticConfig:
        """Создает пустую конфигурацию для fallback."""
        return SemanticConfig(skip_keywords=[], discount_keywords=[], weight_patterns=[], tax_patterns=[])

    def process(
        self, 
        layout: LayoutResult, 
        locale: LocaleResult, 
        store: StoreResult, 
        metadata: MetadataResult
    ) -> SemanticResult:
        """
        Извлекает товары из чека.
        
        Координирует работу всех модулей:
        1. Загрузка конфига
        2. Определение границ товарной зоны
        3. Итерация по строкам с классификацией
        4. Парсинг товаров
        5. Валидация цен
        6. Сборка результата
        """
        # 1. Загрузка конфига
        try:
            full_config = self.config_loader.load(locale.locale_code, store.store_name)
            semantic_config = full_config.semantic
        except Exception as e:
            logger.warning(f"[SemanticStage] Ошибка загрузки конфига: {e}")
            semantic_config = self._empty_semantic_config()
        
        # 2. Определение границ товарной зоны
        start_line, end_line = self.line_classifier.find_items_zone(layout, store, metadata)
        
        # 3. Инициализация результатов
        items: List[ParsedItem] = []
        discounts: List[ParsedItem] = []
        skipped = 0
        parsed = 0
        
        # Контекстный буфер для многострочных названий
        name_buffer = []
        
        # 4. Итерация по строкам
        for i, line in enumerate(layout.lines):
            # 4.1. Пропуски за границами товарной зоны
            if i < start_line or i > end_line:
                skipped += 1
                continue
            
            # 4.2. Footer Protector
            if self.line_classifier.is_footer_line(line, i, metadata):
                logger.debug(f"[SemanticStage] Footer Protector: Stop parsing at line {i}")
                break
            
            # 4.3. Header Protector
            if self.line_classifier.is_header_line(line, layout, semantic_config):
                logger.debug(f"[SemanticStage] Header Protector: Skip line '{line.text}'")
                name_buffer = []  # Сброс буфера
                skipped += 1
                continue
            
            # 4.4. Служебные строки
            if self.line_classifier.should_skip(line.text, semantic_config):
                name_buffer = []  # Сброс буфера
                skipped += 1
                continue
            
            # 4.5. Геометрический сплиттинг
            sub_lines = self.item_parser.split_by_geometry(line, semantic_config.line_split_y_threshold)
            
            # 4.6. Парсинг каждой подстроки
            for sub_line in sub_lines:
                line_items = self.item_parser.parse(sub_line, semantic_config)
                
                if line_items:
                    for item in line_items:
                        # 4.7. Price Sanity Check
                        receipt_total = metadata.receipt_total or 0
                        is_valid, corrected_price = self.price_extractor.validate(
                            item.total, 
                            receipt_total, 
                            len(items)
                        )
                        
                        # Если цена аномальна, пробуем исправить
                        if not is_valid and receipt_total > 0:
                            # Ищем цену в исходной строке для Smart Cleaner
                            price_strings = self.price_extractor.extract_strings(sub_line.text)
                            if price_strings:
                                cleaned_price = self.price_extractor.clean_outlier(
                                    price_strings[0],
                                    receipt_total,
                                    semantic_config.clean_outliers_strategy if semantic_config else None
                                )
                                
                                if cleaned_price:
                                    logger.info(f"[SemanticStage] Smart Cleaner: {item.total} -> {cleaned_price}")
                                    item.total = cleaned_price
                                    item.price = cleaned_price
                                    is_valid = True
                        
                        # Если после всех попыток цена всё ещё аномальна - пропускаем
                        if not is_valid and receipt_total >= 20:
                            logger.warning(f"[SemanticStage] Price Sanity Check: Ignore '{item.name}' with price {item.total}")
                            continue
                        
                        # 4.8. Буфер имени (для многострочных названий)
                        cleaned_name = self.item_parser.clean_name(item.name)
                        if (not cleaned_name or cleaned_name.replace('.', '').replace(',', '').isdigit()) and name_buffer:
                            item.name = " ".join(name_buffer) + " " + item.name
                            name_buffer = []  # Использовали буфер
                        
                        # 4.9. Добавление в результат
                        parsed += 1
                        if item.is_discount:
                            discounts.append(item)
                        else:
                            items.append(item)
                else:
                    # 4.10. Возможно это часть названия (многострочное название)
                    potential_name = self.item_parser.clean_name(sub_line.text)
                    if potential_name and len(potential_name) > 3:
                        name_buffer.append(potential_name)
                        max_buffer = semantic_config.name_buffer_size if semantic_config else 3
                        if len(name_buffer) > max_buffer:
                            name_buffer.pop(0)  # Ограничиваем размер буфера
        
        # 5. Сборка результата
        return SemanticResult(
            items=items,
            discounts=discounts,
            skipped_lines=skipped,
            parsed_lines=parsed
        )
