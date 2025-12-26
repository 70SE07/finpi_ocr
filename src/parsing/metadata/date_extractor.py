import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from loguru import logger

from config.settings import MAX_YEAR_OFFSET_PAST, MAX_YEAR_OFFSET_FUTURE

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

@dataclass
class DateResult:
    """Результат извлечения даты."""
    date: Optional[datetime]
    text: str
    confidence: float = 0.0

class DateExtractor:
    """
    Извлекает дату транзакции из текста чека.
    Поддерживает мультиязычные форматы через LocaleConfig.
    """
    
    # Регулярные выражения для популярных форматов дат (fallback)
    PATTERNS = [
        # DD.MM.YYYY (Германия, Украина, Болгария, Польша)
        r"(\d{2})\s?[.,]\s?(\d{2})\s?[.,]\s?(20\d{2})",
        # DD/MM/YYYY or DD/MM/YY (Португалия, Англия)
        r"(\d{2})/(\d{2})/(20\d{2}|\d{2})",
        # YYYY-MM-DD (ISO, Турция)
        r"(20\d{2})-(\d{2})-(\d{2})",
        # DD MM YYYY (Иногда OCR заменяет точки на пробелы)
        r"(\d{2})\s{1,2}(\d{2})\s{1,2}(20\d{2})",
        # DD.MM.YY (Короткий формат) (Допускаем пробелы)
        r"(\d{2})\s?[.,]\s?(\d{2})\s?[.,]\s?(\d{2})",
    ]

    # Ключевые слова для даты (fallback)
    DATE_KEYWORDS = [r"datum", r"data", r"date", r"дата", r"дата чека"]

    def extract(
        self, 
        texts: List[str],
        locale_config: Optional['LocaleConfig'] = None
    ) -> DateResult:
        """
        Ищет дату во всем тексте чека.
        
        Args:
            texts: Список строк чека
            locale_config: Конфигурация локали (опционально)
        """
        if locale_config and locale_config.date:
            # Используем паттерны из locale_config
            logger.debug(f"[DateExtractor] Используем форматы из {locale_config.code}: {locale_config.date.formats}")
            patterns = self._build_patterns_from_locale(locale_config.date.formats)
        else:
            # Fallback: используем встроенные паттерны
            patterns = self.PATTERNS
            logger.debug("[DateExtractor] Используем fallback паттерны")
        
        all_text = "\n".join(texts)
        lower_text = all_text.lower()
        
        valid_dates = []
        current_year = datetime.now().year
        
        for p in patterns:
            matches = re.finditer(p, all_text)
            for m in matches:
                try:
                    # Парсинг в зависимости от паттерна
                    dt = self._parse_date_match(m, p)
                    
                    if dt:
                        # Приоритет, если рядом есть слово "Дата/Datum"
                        context_start = max(0, m.start() - 30)
                        context_end = min(len(all_text), m.end() + 10)
                        context = lower_text[context_start:context_end]
                        
                        confidence = 0.7
                        if any(re.search(kw, context) for kw in self.DATE_KEYWORDS):
                            confidence = 0.95
                        
                        # Базовая валидация: год в допустимом диапазоне
                        now = datetime.now()
                        year_min = now.year - MAX_YEAR_OFFSET_PAST
                        year_max = now.year + MAX_YEAR_OFFSET_FUTURE
                        
                        if year_min <= dt.year <= year_max:
                            logger.debug(f"[DateExtractor] Валидная дата найдена: {dt.strftime('%Y-%m-%d')} (conf={confidence})")
                            valid_dates.append(DateResult(date=dt, text=m.group(0), confidence=confidence))
                        else:
                            logger.trace(f"[DateExtractor] Дата {dt.year} вне диапазона [{year_min}-{year_max}]")
                except (ValueError, IndexError) as e:
                    logger.trace(f"[DateExtractor] Ошибка парсинга даты: {e}")
                    continue
        
        if valid_dates:
            # Сортируем по confidence, затем по близости к текущему году
            valid_dates.sort(key=lambda x: x.confidence, reverse=True)
            return valid_dates[0]
            
        return DateResult(date=None, text="", confidence=0.0)
    
    def _build_patterns_from_locale(self, formats: List[str]) -> List[str]:
        """
        Строит regex паттерны из форматов дат из locale_config.
        
        Пример: "DD.MM.YYYY" → r"(\d{2})\.(\d{2})\.(20\d{2})"
        """
        patterns = []
        for fmt in formats:
            fmt = fmt.strip()
            pattern = fmt
            
            # Заменяем компоненты на regex
            pattern = pattern.replace("DD", r"(\d{2})")
            pattern = pattern.replace("MM", r"(\d{2})")
            pattern = pattern.replace("YYYY", r"(20\d{2})")
            pattern = pattern.replace("YY", r"(\d{2})")
            
            # Экранируем разделители
            for sep in [".", "/", "-"]:
                pattern = pattern.replace(sep, r"\s?" + sep + r"\s?")
            
            patterns.append(pattern)
        
        logger.debug(f"[DateExtractor] Построены паттерны: {patterns}")
        return patterns
    
    def _parse_date_match(self, match, pattern: str) -> Optional[datetime]:
        """
        Парсит дату из match в зависимости от паттерна.
        """
        groups = match.groups()
        
        try:
            # Определяем формат по паттерну
            if "YYYY" in pattern:
                if pattern.find("DD") < pattern.find("MM"):
                    # DD.MM.YYYY
                    d, m_val, y = groups[0], groups[1], groups[2]
                else:
                    # YYYY-MM-DD
                    y, m_val, d = groups[0], groups[1], groups[2]
            else:
                # DD.MM.YY
                d, m_val, y = groups[0], groups[1], groups[2]
                if len(y) == 2:
                    y = "20" + y
            
            # Конвертируем в int
            d, m_val, y = int(d), int(m_val), int(y)
            
            return datetime(y, m_val, d)
        except (ValueError, IndexError, TypeError):
            return None


