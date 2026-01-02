"""
Semantic Extraction Operation: Семантическое извлечение цен и товаров.

ЦКП: Список распознанных товаров (items) с детальным следом анализа каждой операции.
"""

from typing import List, Dict, TYPE_CHECKING, Optional
from ..dto import TextBlock
from . import (
    PriceParser,
    TaxParser,
    QuantityParser,
    LineClassifier,
    LineType,
    MathChecker,
    DecimalFixer,
    CyrillicFixer,
    GhostSuffixFixer
)
from loguru import logger

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

class SemanticExtractor:
    """
    Оркестратор извлечения: координирует работу атомарных модулей.
    
    Поддерживает LocaleConfig для локализации цен и классификации.
    """
    
    def __init__(self, locale_config: Optional['LocaleConfig'] = None):
        """
        Args:
            locale_config: Конфигурация локали (опционально)
        """
        self.locale_config = locale_config
        self.price_parser = PriceParser(locale_config=locale_config)
        self.tax_parser = TaxParser()
        self.qty_parser = QuantityParser(locale_config=locale_config)
        self.classifier = LineClassifier(locale_config=locale_config)
        self.math_checker = MathChecker()
        
        # Конфигурируемый порядок фиксов
        self.fixers = []
        
        if locale_config and locale_config.extractors and locale_config.extractors.semantic_extraction:
            fixer_names = locale_config.extractors.semantic_extraction.get("fixers", [])
            
            for fixer_name in fixer_names:
                if fixer_name == "cyrillic_fixer":
                    self.fixers.append(CyrillicFixer())
                elif fixer_name == "ghost_suffix_fixer":
                    self.fixers.append(GhostSuffixFixer())
                elif fixer_name == "decimal_fixer":
                    self.fixers.append(DecimalFixer())
        else:
            # Fallback: дефолтный порядок
            self.fixers = [
                CyrillicFixer(),
                GhostSuffixFixer(),
                DecimalFixer()
            ]

    def process(self, lines: List[TextBlock]) -> dict:
        """
        Выполняет поэтапный анализ каждой строки.
        
        Returns:
            dict: {
                "items": List[dict],  # Чистый результат
                "trace": List[dict]   # Детальный след для отладки
            }
        """
        items = []
        trace = []
        
        for line_block in lines:
            text = line_block.text
            
            # 0. Исправление признаков (Legacy Vectors)
            # Применяем фиксы в конфигурируемом порядке
            processed_text = text
            for fixer in self.fixers:
                fix_res = fixer.fix(processed_text)
                processed_text = fix_res.text
            
            # 1. Поиск цены
            price = self.price_parser.parse(processed_text)
            if price:
                logger.trace(f"[Extraction] Найдена цена {price} в строке: '{processed_text}'")
            
            # 2. Поиск налога
            tax = self.tax_parser.parse(processed_text)
            
            # 3. Поиск количества
            qty_res = self.qty_parser.parse(processed_text)
            if qty_res:
                logger.trace(f"[Extraction] Найдено кол-во {qty_res.qty} в строке: '{processed_text}'")
            
            # 4. Классификация строки
            line_type = self.classifier.classify(
                text, 
                has_price=(price is not None),
                has_qty=(qty_res is not None)
            )
            
            # 5. Математическая проверка (если есть цена и количество)
            math_res = None
            if qty_res and price:
                math_res = self.math_checker.verify(qty_res.qty, qty_res.unit_price, price)
            
            # Формируем след анализа (Trace)
            line_trace = {
                "text": text,
                "processed_text": processed_text if fix_res.was_fixed else None,
                "type": line_type.value,
                "extraction": {
                    "price": float(price) if price else None,
                    "tax": tax,
                    "decimal_fix": {
                        "applied": fix_res.was_fixed,
                        "count": fix_res.count
                    },
                    "cyrillic_fix": {
                        "applied": cyr_res.was_fixed,
                        "replacements": cyr_res.replacements
                    },
                    "ghost_suffix_fix": {
                        "applied": ghost_res.was_fixed,
                        "removed": ghost_res.removed_suffix
                    },
                    "qty": {
                        "value": float(qty_res.qty) if qty_res else None,
                        "unit_price": float(qty_res.unit_price) if qty_res and qty_res.unit_price else None
                    },
                    "math": {
                        "is_valid": math_res.is_valid if math_res else None,
                        "difference": float(math_res.difference) if math_res else 0.0
                    }
                }
            }
            logger.debug(f"[Extraction] Строка классифицирована как {line_type.value}: '{text}'")
            trace.append(line_trace)
            
            # Если это товар — добавляем в итоговый список
            if line_type == LineType.ITEM:
                items.append({
                    "name": processed_text,
                    "price": float(price) if price else 0.0,
                    "tax": tax,
                    "qty": float(qty_res.qty) if qty_res else 1.0,
                    "is_discount": float(price) < 0 if price else False
                })
            elif line_type == LineType.DISCOUNT:
                items.append({
                    "name": processed_text,
                    "price": float(price) if price else 0.0,
                    "tax": tax,
                    "qty": 1.0,
                    "is_discount": True
                })
                
        return {
            "items": items,
            "trace": trace
        }


