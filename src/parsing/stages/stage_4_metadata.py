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
        
        # Загружаем конфиг для локали
        config = self.config_loader.load(locale.locale_code)
        
        # Извлекаем дату
        receipt_date, date_raw = self._extract_date(layout)
        
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
        self, layout: LayoutResult
    ) -> Tuple[Optional[date], Optional[str]]:
        """
        Извлекает дату из чека.
        
        Использует хардкоженные паттерны (логика).
        Паттерны зависят от региона, а не от языка.
        """
        # Хардкоженные паттерны дат — это логика, не данные
        # Остаються в коде (ADR-013: логика в коде, данные в конфигах)
        patterns = self.DATE_PATTERNS.get("default", [])
        
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
            
            for keyword in keywords:
                if keyword in line_lower:
                    total, raw = self._extract_price_from_line(line.text)
                    if total is not None and total > 0:
                        # Вес: строки ниже имеют больший приоритет
                        candidates.append((total, raw, i))
                        logger.debug(f"[Stage 4] Кандидат: '{line.text}' -> {total} (keyword: {keyword})")
                    break  # Одно ключевое слово достаточно
        
        if candidates:
            # Сортируем: сначала по позиции (ниже = лучше), потом по сумме (больше = лучше)
            # Выбираем строку с наибольшей суммой из нижней половины
            lower_half = [c for c in candidates if c[2] >= total_lines // 2]
            if lower_half:
                best = max(lower_half, key=lambda x: x[0])
            else:
                best = max(candidates, key=lambda x: x[0])
            
            logger.debug(f"[Stage 4] Выбрана сумма: {best[0]} из строки {best[2]}")
            return best[0], best[1], best[2]
        
        # Fallback: наибольшая сумма в нижней трети чека
        logger.debug("[Stage 4] Fallback: поиск наибольшей суммы в нижней трети")
        lower_third_start = total_lines * 2 // 3
        max_total = None
        max_raw = None
        max_line = -1
        
        for i in range(lower_third_start, total_lines):
            line = layout.lines[i]
            total, raw = self._extract_price_from_line(line.text)
            if total is not None and total > 1.0:
                if max_total is None or total > max_total:
                    max_total = total
                    max_raw = raw
                    max_line = i
        
        if max_total is not None:
            logger.debug(f"[Stage 4] Fallback: выбрана сумма {max_total} из строки {max_line}")
        
        return max_total, max_raw, max_line
    
    def _extract_price_from_line(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """Извлекает цену из строки."""
        # Паттерны цен
        patterns = [
            r"(\d+)[,.](\d{2})\s*(?:EUR|€|PLN|zł|CZK|Kč)?",  # 12,34 EUR
            r"(?:EUR|€|PLN|zł)\s*(\d+)[,.](\d{2})",          # EUR 12,34
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
