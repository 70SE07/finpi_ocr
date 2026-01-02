"""
Stage 5: Semantic Extraction (Hardened Version)

ЦКП: Извлечение товаров с учетом вертикального контекста (многострочность).
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
    def __init__(self, config_loader: Optional[ConfigLoader] = None, config: Optional[LocaleConfig] = None):
        self.config_loader = config_loader or ConfigLoader()
        self.config = config

    def _empty_semantic_config(self) -> "SemanticConfig":
        from ..locales.config_loader import SemanticConfig
        return SemanticConfig(skip_keywords=[], discount_keywords=[], weight_patterns=[], tax_patterns=[])

    def process(self, layout: LayoutResult, locale: LocaleResult, store: StoreResult, metadata: MetadataResult) -> SemanticResult:
        try:
            # Загружаем конфиг для локали (с учетом магазина)
            full_config = self.config_loader.load(locale.locale_code, store.store_name)
            semantic_config = full_config.semantic
        except Exception as e:
            logger.warning(f"[SemanticStage] Ошибка загрузки конфига: {e}")
            semantic_config = self._empty_semantic_config()
        
        items: List[ParsedItem] = []
        discounts: List[ParsedItem] = []
        skipped = 0
        parsed = 0
        
        start_line = self._find_items_start(layout, store)
        end_line = self._find_items_end(layout, metadata)
        
        # Контекстный буфер для многострочных названий
        name_buffer = []
        
        for i, line in enumerate(layout.lines):
            # 1. Пропуски за границами
            if i < start_line or i > end_line:
                skipped += 1
                continue
            
            # 1.1 Footer Protector: Останавливаем поиск товаров после итоговой суммы
            # (если строка с итогом была надежно определена в Stage 4)
            if metadata.total_line_number != -1 and i > metadata.total_line_number:
                # В Германии иногда Pfand/Скидка может быть сразу под итогом (редко, но бывает)
                # Поэтому даем запас в 1 строку или проверяем ключевые слова
                is_footer_meta = any(kw in line.text.lower() for kw in ['steuer', 'mwst', 'vat', 'ptu', 'netto', 'brutto'])
                if is_footer_meta or i > metadata.total_line_number + 1:
                    logger.debug(f"[Stage 5] Footer Protector: Stop parsing at line {i} (Total was at {metadata.total_line_number})")
                    break
            
            # 2. Header Protector: Блокировка технических заголовков в верхней части чека
            if line.y_position < layout.image_height / 3:
                is_header = False
                for identifier in semantic_config.legal_header_identifiers:
                    if identifier.lower() in line.text.lower():
                        logger.debug(f"[Stage 5] Header Protector: Skip line '{line.text}' due to identifier '{identifier}'")
                        is_header = True
                        break
                if is_header:
                    name_buffer = [] # Сброс контекста
                    skipped += 1
                    continue

            # 3. Служебные строки (skip_keywords)
            if self._should_skip_line(line.text, semantic_config):
                name_buffer = [] 
                skipped += 1
                continue

            # 4. Геометрический сплиттинг
            sub_lines = self._split_line_by_geometry(line, semantic_config.line_split_y_threshold)
            
            for sub_line in sub_lines:
                # 5. Парсинг компонентов (цена, кол-во)
                line_items = self._parse_item_line(sub_line, semantic_config)
                
                if line_items:
                    for item in line_items:
                        # 6. Price Sanity Check & Smart Cleaning
                        # Если цена товара аномальна, пробуем её очистить от префиксного шума
                        receipt_total = metadata.receipt_total or 0
                        is_outlier = False
                        
                        # Аномалия 1: Цена тупо больше итога
                        if receipt_total > 0 and item.total > receipt_total:
                            is_outlier = True
                            
                        # Аномалия 2: Адаптивный порог
                        # Для маленьких чеков (< 20 EUR/PLN) порог не применяется - 
                        # там каждый товар естественно составляет большую долю
                        # Для средних (< 50): порог 50%
                        # Для больших: порог 40% (короткие) или 25% (длинные)
                        if not is_outlier and receipt_total >= 20:
                            if receipt_total < 50:
                                threshold = 0.5  # 50% для средних чеков
                            else:
                                threshold = 0.4 if len(items) <= 5 else 0.25
                            if item.total > receipt_total * threshold:
                                is_outlier = True

                        if is_outlier:
                            original_total = item.total
                            # Ищем паттерн цены в конце исходной строки
                            price_match = re.search(r"(\d+[\.,]\d{2})", sub_line.text)
                            if price_match:
                                price_str = price_match.group(1).replace(',', '.')
                                # Глубокая очистка: пробуем отсекать цифры слева, пока цена не станет <= итога
                                # (Например: 923.39 -> 23.39 -> 3.39)
                                # Применяем ТОЛЬКО если включена стратегия deep_prefix
                                if semantic_config and semantic_config.clean_outliers_strategy == "deep_prefix":
                                    current_price_str = price_str
                                    while len(current_price_str) > 3: # Минимум X.XX
                                        try:
                                            candidate_price = float(current_price_str)
                                            # Если цена стала <= итога и вменяемая - берем!
                                            threshold_multiplier = 0.5
                                            if 0 < candidate_price <= receipt_total * threshold_multiplier:
                                                logger.info(f"[Stage 5] Smart Cleaner: Corrected Outlier {original_total} -> {candidate_price}")
                                                item.total = candidate_price
                                                item.price = candidate_price
                                                break
                                        except ValueError: pass
                                        current_price_str = current_price_str[1:] # Отсекаем одну цифру слева
                                
                                    if item.total != original_total:
                                        logger.info(f"[Stage 5] Smart Cleaner: Salvation successful! New price: {item.total}")
                                        is_outlier = False # Снимаем флаг аномалии, так как мы её исправили!
                            
                            # Если после всех попыток чистки это всё еще аномалия - вот тогда игнорируем
                            # (но только для чеков >= 20, для маленьких не фильтруем)
                            if is_outlier and receipt_total >= 20:
                                if receipt_total < 50:
                                    threshold = 0.5
                                else:
                                    threshold = 0.4 if len(items) <= 5 else 0.25
                                if item.total > receipt_total * threshold:
                                    logger.warning(f"[Stage 5] Price Sanity Check: Ignore suspicious item '{item.name}' with price {item.total}")
                                    continue

                        # Если у товара нет имени или имя - просто число/мусор, берем из буфера
                        cleaned_name = self._clean_item_name(item.name)
                        if (not cleaned_name or cleaned_name.replace('.', '').replace(',', '').isdigit()) and name_buffer:
                            item.name = " ".join(name_buffer) + " " + item.name
                            name_buffer = [] # Использовали буфер
                        
                        parsed += 1
                        if item.is_discount:
                            discounts.append(item)
                        else:
                            items.append(item)
                else:
                    # Если ничего не распарсилось, возможно это часть названия
                    potential_name = self._clean_item_name(sub_line.text)
                    if potential_name and len(potential_name) > 3:
                        name_buffer.append(potential_name)
                        # Ограничиваем буфер, используя конфиг (по умолчанию 3)
                        max_buffer = semantic_config.name_buffer_size if semantic_config else 3
                        if len(name_buffer) > max_buffer:
                            name_buffer.pop(0)
        
        return SemanticResult(items=items, discounts=discounts, skipped_lines=skipped, parsed_lines=parsed)

    def _find_items_start(self, layout: LayoutResult, store: StoreResult) -> int:
        if store.matched_in_line >= 0:
            return min(store.matched_in_line + 2, len(layout.lines) - 1)
        return 2

    def _find_items_end(self, layout: LayoutResult, metadata: MetadataResult) -> int:
        if metadata.total_line_number >= 0:
            return max(0, metadata.total_line_number - 1)
        return max(0, len(layout.lines) - 5)

    def _should_skip_line(self, text: str, config: "SemanticConfig") -> bool:
        text_lower = text.lower()
        if len(text.strip()) < 2: return True
        for keyword in config.skip_keywords:
            if keyword in text_lower: return True
        for pattern in config.weight_patterns:
            if re.search(pattern, text, re.IGNORECASE): return True
        for pattern in config.tax_patterns:
            if re.search(pattern, text.strip(), re.IGNORECASE): return True
        return False

    def _split_line_by_geometry(self, line: Line, threshold: int) -> List[Line]:
        if not line.words or len(line.words) < 2: return [line]
        sorted_words = sorted(line.words, key=lambda w: w.bounding_box.y)
        clusters = []
        current_cluster = [sorted_words[0]]
        for i in range(1, len(sorted_words)):
            w = sorted_words[i]
            prev_w = current_cluster[-1]
            if abs(w.bounding_box.y - prev_w.bounding_box.y) > threshold:
                clusters.append(current_cluster)
                current_cluster = [w]
            else:
                current_cluster.append(w)
        clusters.append(current_cluster)
        if len(clusters) == 1: return [line]
        new_lines = []
        for cluster in clusters:
            sorted_cluster = sorted(cluster, key=lambda w: w.bounding_box.x)
            text = " ".join([w.text for w in sorted_cluster])
            new_lines.append(Line(text=text, words=sorted_cluster, y_position=min(w.bounding_box.y for w in cluster),
                                 x_min=min(w.bounding_box.x for w in cluster), 
                                 x_max=max(w.bounding_box.x + w.bounding_box.width for w in cluster),
                                 confidence=sum(w.confidence for w in cluster)/len(cluster), line_number=line.line_number))
        return new_lines

    def _parse_item_line(self, line: Line, config: LocaleConfig) -> List[ParsedItem]:
        text = line.text
        # Сначала пробуем разделить по нескольким ценам
        prices = re.findall(r"(?<![\d.,])\-?\d+[.,]\d{2}(?![\d.,])", text)
        if len(prices) >= 2:
            # Ищем маркеры умножения более гибко (включая начало строки)
            has_explicit_multi = bool(re.search(r"(\*|[\s*x×X]\s+)", text.upper())) or \
                               any(op in text.upper() for op in [' VAT ', ' IVA ', ' PTU '])
            
            # Системное решение: Паттерн весового товара без знака умножения
            # Формат: "NAME qty price total TAX" (польский Carrefour)
            # Пример: "C_CYTRYNY LUZ 0,29 9,99 2,90 C"
            # Где qty < 10, qty * price ≈ total (с погрешностью 0.02)
            is_weight_pattern = False
            if len(prices) == 3 and not has_explicit_multi:
                try:
                    qty = float(prices[0].replace(',', '.'))
                    unit_price = float(prices[1].replace(',', '.'))
                    total = float(prices[2].replace(',', '.'))
                    # Проверка: qty < 10 (типичный вес), и qty * price ≈ total
                    if qty < 10 and abs(qty * unit_price - total) < 0.02:
                        is_weight_pattern = True
                        logger.debug(f"[Stage 5] Weight Pattern detected: qty={qty}, price={unit_price}, total={total}")
                except ValueError:
                    pass
            
            should_split = False
            if not has_explicit_multi and len(prices) >= 2 and not is_weight_pattern:
                should_split = True
            elif has_explicit_multi and len(prices) >= 4: # Если 4+ цены при наличии X, это уже перебор
                should_split = True
            
            if should_split:
                # Ищем последнюю цену и пробуем откусить её
                last_price_match = list(re.finditer(r"(?<![\d.,])\-?\d+[.,]\d{2}(?![\d.,])", text))[-1]
                pos = last_price_match.start()
                
                part1, part2 = text[:pos].strip(), text[pos:].strip()
                logger.debug(f"[Stage 5] Multi-Price Split discovered: '{part1}' | '{part2}'")
                
                res1 = self._parse_item_line(Line(text=part1, words=[], y_position=line.y_position, line_number=line.line_number), config)
                res2 = self._parse_item_line(Line(text=part2, words=[], y_position=line.y_position, line_number=line.line_number), config)
                if res1 and res2: return res1 + res2

        name, quantity, price, total = self._extract_item_components(text, config)
        if total is not None:
            is_discount = self._is_discount_line(name or text, config.discount_keywords)
            return [ParsedItem(name=name or "", quantity=quantity, price=price, total=total, is_discount=is_discount, line_number=line.line_number, raw_text=text)]
        return []

    def _is_discount_line(self, text: str, discount_keywords: List[str]) -> bool:
        text_lower = text.lower()
        # Если есть "Pfand" (залог), это НЕ скидка, но это спец-позиция.
        # В нашей системе мы считаем скидкой всё, что уменьшает чек, 
        # но залог (возврат) может быть и отрицательным и положительным.
        if "pfand" in text_lower or "leergut" in text_lower:
             return False

        if any(kw in text_lower for kw in discount_keywords): return True
        return bool(re.search(r"-\s*\d+[,\.]\d{2}\s*$", text))

    def _extract_item_components(self, text: str, config: "SemanticConfig" = None) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
        # Стандартный паттерн (требует разделителя слева)
        standard_pattern = r"(?<![\d.,])(-?\d+)[.,](\d{2})(?=\s*($|[A-Z%€£$]|zł|Kč))"
        # Relaxed паттерн для склеенных цен (Aldi), включается через конфиг
        relaxed_pattern = r"(-?\d+)[.,](\d{2})(?=\s*($|[A-Z%€£$]|zł|Kč))"
        
        price_pattern = standard_pattern
        if config and config.allow_joined_prices:
            price_pattern = relaxed_pattern
            
        prices = re.findall(price_pattern, text)
        if not prices: return None, None, None, None
        
        total = float(f"{prices[-1][0]}.{prices[-1][1]}")
        name = text
        for p in prices:
            name = name.replace(f"{p[0]},{p[1]}", "").replace(f"{p[0]}.{p[1]}", "")
        
        name = self._clean_item_name(name)
        quantity, price = None, None
        
        # Паттерн 1: Явный маркер умножения (1*5.99, 0.5 x 9.99)
        qty_pattern = r"(?:^|\s)(\d{1,3}(?:[.,]\d{1,3})?)\s*[xX×*]\s*(?:\d|$)"
        qty_match = re.search(qty_pattern, text)
        if qty_match:
            try:
                quantity = float(qty_match.group(1).replace(",", "."))
                if len(prices) >= 2:
                    price = float(f"{prices[0][0]}.{prices[0][1]}")
            except: pass
        
        # Паттерн 2: Весовой товар без маркера (qty price total) - польский формат
        # Пример: "C_CYTRYNY LUZ 0,29 9,99 2,90 C"
        if quantity is None and len(prices) == 3:
            try:
                qty_candidate = float(f"{prices[0][0]}.{prices[0][1]}")
                price_candidate = float(f"{prices[1][0]}.{prices[1][1]}")
                total_candidate = float(f"{prices[2][0]}.{prices[2][1]}")
                # Проверка: qty < 10 и qty * price ≈ total
                if qty_candidate < 10 and abs(qty_candidate * price_candidate - total_candidate) < 0.02:
                    quantity = qty_candidate
                    price = price_candidate
                    total = total_candidate
                    logger.debug(f"[Stage 5] Weight item extracted: qty={quantity}, price={price}, total={total}")
            except ValueError:
                pass
        
        return name, quantity, price, total

    def _clean_item_name(self, name: str) -> str:
        name = re.sub(r"[xX×]\s*$", "", name)
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"^[\s\-\*]+", "", name)
        name = re.sub(r"[\s\-\*]+$", "", name).strip()
        # Убираем одиночные буквы налогов в конце
        name = re.sub(r"\s+[A-Z]\s*$", "", name)
        return name
