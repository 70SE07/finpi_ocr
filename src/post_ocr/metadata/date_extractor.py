import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from loguru import logger

from config.settings import MAX_YEAR_OFFSET_PAST, MAX_YEAR_OFFSET_FUTURE

@dataclass
class DateResult:
    """Результат извлечения даты."""
    date: Optional[datetime]
    text: str
    confidence: float = 0.0

class DateExtractor:
    """
    Извлекает дату транзакции из текста чека.
    Поддерживает мультиязычные форматы.
    """
    
    # Регулярные выражения для популярных форматов дат
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

    # Ключевые слова для даты
    DATE_KEYWORDS = [r"datum", r"data", r"date", r"дата", r"дата чека"]

    def extract(self, texts: List[str]) -> DateResult:
        """
        Ищет дату во всем тексте чека.
        """
        all_text = "\n".join(texts)
        lower_text = all_text.lower()
        
        valid_dates = []
        current_year = datetime.now().year
        
        for p in self.PATTERNS:
            matches = re.finditer(p, all_text)
            for m in matches:
                try:
                    if p == self.PATTERNS[0]: # DD.MM.YYYY
                        d, m_val, y = m.groups()
                        dt = datetime(int(y), int(m_val), int(d))
                    elif p == self.PATTERNS[1]: # DD/MM/YYYY or DD/MM/YY
                        d, m_val, y = m.groups()
                        if len(y) == 2: y = "20" + y
                        dt = datetime(int(y), int(m_val), int(d))
                    elif p == self.PATTERNS[2]: # YYYY-MM-DD
                        y, m_val, d = m.groups()
                        dt = datetime(int(y), int(m_val), int(d))
                    elif p == self.PATTERNS[3]: # DD MM YYYY
                        d, m_val, y = m.groups()
                        dt = datetime(int(y), int(m_val), int(d))
                    elif p == self.PATTERNS[4]: # DD.MM.YY
                        d, m_val, y = m.groups()
                        dt = datetime(2000 + int(y), int(m_val), int(d))
                    

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
