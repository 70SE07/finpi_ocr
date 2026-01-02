"""
Stage 4: Metadata Extraction

ЦКП: Извлечение метаданных чека (дата, итоговая сумма).

Входные данные: LayoutResult, LocaleResult, StoreResult
Выходные данные: MetadataResult (дата, сумма, валюта)

Алгоритм:
1. Поиск даты по regex-паттернам локали
2. Поиск итоговой суммы по ключевым словам
3. Определение валюты по локали
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from .stage_1_layout import LayoutResult
from .stage_2_locale import LocaleResult
from .stage_3_store import StoreResult
from ..locales.config_loader import ConfigLoader, ParsingConfig


@dataclass
class MetadataResult:
    """
    Результат Stage 4: Metadata Extraction.
    
    ЦКП: Метаданные чека.
    """
    receipt_date: Optional[date] = None         # Дата чека
    receipt_total: Optional[float] = None       # Итоговая сумма
    currency: str = "EUR"                       # Валюта
    date_raw: Optional[str] = None              # Сырая строка даты
    total_raw: Optional[str] = None             # Сырая строка суммы
    total_line_number: int = -1                 # Номер строки с суммой
    
    def to_dict(self) -> dict:
        return {
            "receipt_date": self.receipt_date.isoformat() if self.receipt_date else None,
            "receipt_total": self.receipt_total,
            "currency": self.currency,
            "date_raw": self.date_raw,
            "total_raw": self.total_raw,
            "total_line_number": self.total_line_number,
        }


class MetadataStage:
    """
    Stage 4: Metadata Extraction.
    
    ЦКП: Извлечение даты и итоговой суммы.
    
    Загружает конфигурацию локали (ключевые слова для итоговой суммы, валюта).
    """
    
    # Хардкоженные паттерны дат (остаються в коде — это логика, не данные)
    DATE_PATTERNS: Dict[str, List[str]] = {
        "de_DE": [
            r"(\d{2})\.(\d{2})\.(\d{4})",    # 31.12.2024
            r"(\d{2})\.(\d{2})\.(\d{2})",    # 31.12.24
            r"(\d{4})-(\d{2})-(\d{2})",      # 2024-12-31 (иногда в Lidl)
        ],
        "pl_PL": [
            r"(\d{4})-(\d{2})-(\d{2})",      # 2024-12-31 (ISO)
            r"(\d{2})\.(\d{2})\.(\d{4})",    # 31.12.2024
            r"(\d{2})-(\d{2})-(\d{4})",      # 31-12-2024
        ],
        "es_ES": [
            r"(\d{2})/(\d{2})/(\d{4})",      # 31/12/2024
            r"(\d{2})\.(\d{2})\.(\d{4})",    # 31.12.2024
        ],
        "pt_PT": [
            r"(\d{2})/(\d{2})/(\d{4})",      # 31/12/2024
            r"(\d{2})-(\d{2})-(\d{4})",      # 31-12-2024
        ],
        "default": [
            r"(\d{2})\.(\d{2})\.(\d{4})",    # 31.12.2024
            r"(\d{2})/(\d{2})/(\d{4})",      # 31/12/2024
            r"(\d{4})-(\d{2})-(\d{2})",      # 2024-12-31 (ISO)
        ],
    }
    
    def __init__(
        self,
        config_loader: Optional[ConfigLoader] = None,
    ):
        """
        Args:
            config_loader: Загрузчик конфигов локалей (LocaleConfig)
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
    ) -> MetadataResult:
        """
        Извлекает метаданные из чека.
        
        Args:
            layout: Результат Stage 1
            locale: Результат Stage 2
            store: Результат Stage 3
            
        Returns:
            MetadataResult: Извлечённые метаданные
        """
        logger.debug(f"[Stage 4: Metadata] Извлечение для локали {locale.locale_code}")
        
        # Загружаем конфиг для локали (с учетом магазина)
        config = self.config_loader.load(locale.locale_code, store.store_name)
        
        # Извлекаем дату
        receipt_date, date_raw = self._extract_date(layout, locale.locale_code)
        
        # Извлекаем итоговую сумму (из конфига)
        receipt_total, total_raw, total_line = self._extract_total(layout, config)
        
        # Валюта из конфига
        currency = config.currency
        
        result = MetadataResult(
            receipt_date=receipt_date,
            receipt_total=receipt_total,
            currency=currency,
            date_raw=date_raw,
            total_raw=total_raw,
            total_line_number=total_line,
        )
        
        logger.info(
            f"[Stage 4: Metadata] Дата: {receipt_date}, Сумма: {receipt_total} {currency}"
        )
        
        return result
    
    def _extract_date(
        self, layout: LayoutResult, locale_code: Optional[str] = None
    ) -> Tuple[Optional[date], Optional[str]]:
        """
        Извлекает дату из чека.
        
        Использует хардкоженные паттерны (логика).
        Паттерны зависят от региона, а не от языка.
        """
        # 1. Сначала пробуем локальные паттерны
        locale_patterns = self.DATE_PATTERNS.get(locale_code or "default", [])
        # 2. Потом дефолтные
        default_patterns = self.DATE_PATTERNS.get("default", [])
        all_patterns = list(dict.fromkeys(locale_patterns + default_patterns))

        for line in layout.lines:
            for pattern in all_patterns:
                match = re.search(pattern, line.text)
                if match:
                    try:
                        parsed_date = self._parse_date_match(match, pattern)
                        if parsed_date:
                            return parsed_date, match.group(0)
                    except ValueError:
                        continue
        
        return None, None
        
        for line in layout.lines:
            for pattern in patterns:
                match = re.search(pattern, line.text)
                if match:
                    try:
                        parsed_date = self._parse_date_match(match, pattern)
                        if parsed_date:
                            return parsed_date, match.group(0)
                    except ValueError:
                        continue
        
        return None, None
    
    def _parse_date_match(self, match: re.Match, pattern: str) -> Optional[date]:
        """Парсит найденную дату в зависимости от паттерна."""
        groups = match.groups()
        
        # ISO формат (YYYY-MM-DD)
        if pattern.startswith(r"(\d{4})"):
            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
        # Европейский формат (DD.MM.YYYY или DD/MM/YYYY)
        else:
            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
            # Короткий год (24 -> 2024)
            if year < 100:
                year += 2000
        
        # Валидация
        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
            return date(year, month, day)
        
        return None
    
    def _extract_total(
        self, layout: LayoutResult, config: ParsingConfig
    ) -> Tuple[Optional[float], Optional[str], int]:
        """
        Извлекает итоговую сумму.
        
        Алгоритм:
        1. Ищем строки с ключевыми словами (из конфига локали)
        2. Приоритет строкам в нижней половине чека
        3. Если найдено несколько — берём наибольшую сумму
        4. Fallback: наибольшая сумма в нижней трети чека
        
        Args:
            layout: Результат LayoutStage
            config: Конфигурация локали из parsing.yaml
        """
        keywords = config.total_keywords
        total_lines = len(layout.lines)
        
        # Собираем кандидатов с ключевыми словами
        candidates: List[Tuple[float, str, int]] = []
        for i, line in enumerate(layout.lines):
            line_lower = line.text.lower()
            
            # Пропускаем строки с "сильным" шумом, НО только если там нет Ключевых Слов Итога
            has_total_keyword = any(tk.lower() in line_lower for tk in keywords)
            
            is_noise = False
            if not has_total_keyword:
                for skw in config.semantic.skip_keywords:
                    skw_lower = skw.lower()
                    if skw_lower in line_lower and skw_lower not in [tk.lower() for tk in keywords]:
                        is_noise = True
                        break
            
            if is_noise:
                continue

            for keyword in keywords:
                if keyword in line_lower:
                    total, raw = self._extract_price_from_line(line.text)
                    if total is not None and total > 0:
                        # Вес: строки ниже имеют больший приоритет
                        candidates.append((total, raw, i))
                        logger.debug(f"[Stage 4] Кандидат: '{line.text}' -> {total} (keyword: {keyword})")
                    break  # Одно ключевое слово достаточно
        
        # Системное решение: Весовая логика (Confidence Scoring)
        # STRONG_KEYWORDS (+100): Однозначные маркеры итога к оплате
        # WEAK_KEYWORDS (+20): Контекстные маркеры (валюты, общие слова)
        # Components / Noise: Слова, которые часто путают с итогом (налоги, нетто)
        STRONG_KEYWORDS = {'summe', 'total', 'zahlbetrag', 'gesamtbetrag', 'zu zahlen', 'brutto', 'amount due'}
        WEAK_KEYWORDS = {'betrag', 'gesamt', 'eur', 'euro', '€', 'pay'}
        COMPONENT_KEYWORDS = {'netto', 'mwst', 'vat', 'iva', 'tax', 'steuer', 'net', 'ptu'}

        import math

        scored_candidates: List[Tuple[float, str, int, float]] = [] # (total, raw, line_idx, score)

        for total, raw, i in candidates:
            score = 0.0
            line_text_lower = layout.lines[i].text.lower()
            
            # 1. Вес по ключевым словам
            if any(kw in line_text_lower for kw in STRONG_KEYWORDS):
                score += 100.0
            elif any(kw in line_text_lower for kw in WEAK_KEYWORDS):
                score += 20.0
            elif any(kw in line_text_lower for kw in COMPONENT_KEYWORDS):
                score -= 50.0 # Понижаем вес для налоговых строк
            
            # 2. Вес по позиции (ниже = лучше)
            position_score = (i / total_lines) * 50.0
            score += position_score

            # 3. Вес по размеру (Magnitude)
            # Итоговая сумма почти всегда — самое большое число в подвале
            magnitude_score = math.log10(max(1.0, total)) * 10.0
            score += magnitude_score

            scored_candidates.append((total, raw, i, score))
            logger.debug(f"[Stage 4] Candidate Score: {score:.1f} for '{layout.lines[i].text}' (total={total}, kW={score-position_score-magnitude_score:.0f}, pos={position_score:.1f}, mag={magnitude_score:.1f})")

        if scored_candidates:
            # Выбираем кандидата с максимальным Score
            best = max(scored_candidates, key=lambda x: x[3])
            logger.debug(f"[Stage 4] Systemic Choice: {best[0]} (Score: {best[3]:.1f}) from line {best[2]}")
            return best[0], best[1], best[2]
        
        # Fallback: наибольшая сумма в нижней трети (Score-based)
        logger.debug("[Stage 4] Fallback: Score-based search in lower third")
        lower_third_start = total_lines * 2 // 3
        best_fallback: Optional[Tuple[float, str, int, float]] = None
        
        for i in range(lower_third_start, total_lines):
            total, raw = self._extract_price_from_line(layout.lines[i].text)
            if total is not None and total > 1.0:
                pos_score = (i / total_lines) * 50.0
                mag_score = math.log10(total) * 10.0
                score = pos_score + mag_score
                if best_fallback is None or score > best_fallback[3]:
                    best_fallback = (total, raw, i, score)
        
        if best_fallback:
            logger.debug(f"[Stage 4] Fallback Systemic Choice: {best_fallback[0]} from line {best_fallback[2]}")
            return best_fallback[0], best_fallback[1], best_fallback[2]
        
        return None, None, -1
    
    def _extract_price_from_line(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """Извлекает цену из строки."""
        # Паттерны цен
        patterns = [
            r"(?<![\d.,])(\d+)[,.](\d{2})(?![\d.,])\s*(?:EUR|€|PLN|zł|CZK|Kč)?",  # 12,34 EUR
            r"(?:EUR|€|PLN|zł)\s*(?<![\d.,])(\d+)[,.](\d{2})(?![\d.,])",          # EUR 12,34
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    # Собираем число
                    price = float(f"{groups[0]}.{groups[1]}")
                    return price, match.group(0)
                except (ValueError, IndexError):
                    continue
        
        return None, None
