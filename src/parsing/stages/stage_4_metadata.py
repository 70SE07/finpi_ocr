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
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .stage_1_layout import LayoutResult
from .stage_2_locale import LocaleResult
from .stage_3_store import StoreResult


# Паттерны дат по локалям
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

# Ключевые слова для поиска итоговой суммы
TOTAL_KEYWORDS: Dict[str, List[str]] = {
    "de_DE": ["summe", "gesamt", "gesamtbetrag", "zu zahlen", "total"],
    "pl_PL": ["suma", "razem", "do zaplaty", "total"],
    "es_ES": ["total", "importe", "a pagar"],
    "pt_PT": ["total", "valor", "a pagar"],
    "cs_CZ": ["celkem", "k uhrade"],
    "default": ["total", "sum", "summe"],
}

# Валюты по локалям
CURRENCIES: Dict[str, str] = {
    "de_DE": "EUR",
    "pl_PL": "PLN",
    "es_ES": "EUR",
    "pt_PT": "EUR",
    "cs_CZ": "CZK",
    "bg_BG": "BGN",
    "uk_UA": "UAH",
    "tr_TR": "TRY",
    "th_TH": "THB",
    "en_IN": "INR",
    "default": "EUR",
}


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
    """
    
    def __init__(
        self,
        date_patterns: Optional[Dict[str, List[str]]] = None,
        total_keywords: Optional[Dict[str, List[str]]] = None,
    ):
        self.date_patterns = date_patterns or DATE_PATTERNS
        self.total_keywords = total_keywords or TOTAL_KEYWORDS
    
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
        
        # Извлекаем дату
        receipt_date, date_raw = self._extract_date(layout, locale.locale_code)
        
        # Извлекаем итоговую сумму
        receipt_total, total_raw, total_line = self._extract_total(layout, locale.locale_code)
        
        # Определяем валюту
        currency = CURRENCIES.get(locale.locale_code, CURRENCIES["default"])
        
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
        self, layout: LayoutResult, locale_code: str
    ) -> Tuple[Optional[date], Optional[str]]:
        """Извлекает дату из текста."""
        patterns = self.date_patterns.get(locale_code, self.date_patterns["default"])
        
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
        self, layout: LayoutResult, locale_code: str
    ) -> Tuple[Optional[float], Optional[str], int]:
        """Извлекает итоговую сумму."""
        keywords = self.total_keywords.get(locale_code, self.total_keywords["default"])
        
        # Сканируем снизу вверх (итог обычно в конце)
        for i, line in enumerate(reversed(layout.lines)):
            line_lower = line.text.lower()
            actual_line_num = len(layout.lines) - 1 - i
            
            # Проверяем ключевые слова
            for keyword in keywords:
                if keyword in line_lower:
                    # Ищем число в строке
                    total, raw = self._extract_price_from_line(line.text)
                    if total is not None:
                        return total, raw, actual_line_num
        
        # Fallback: ищем последнюю большую сумму
        for i, line in enumerate(reversed(layout.lines)):
            actual_line_num = len(layout.lines) - 1 - i
            total, raw = self._extract_price_from_line(line.text)
            if total is not None and total > 1.0:
                return total, raw, actual_line_num
        
        return None, None, -1
    
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
