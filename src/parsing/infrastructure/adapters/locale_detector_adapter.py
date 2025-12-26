"""
Адаптер для LocaleDetector, реализующий интерфейс ILocaleDetector (домен Parsing).
"""

from typing import List
from loguru import logger

from ...domain.interfaces import ILocaleDetector
from ...domain.exceptions import LocaleDetectionError
from ...locales.locale_detector import LocaleDetector as OriginalLocaleDetector


class LocaleDetectorAdapter(ILocaleDetector):
    """
    Адаптер для LocaleDetector (домен Parsing).
    
    Реализует интерфейс ILocaleDetector, делегируя вызовы оригинальному LocaleDetector.
    """
    
    def __init__(self):
        """Инициализация адаптера."""
        try:
            self._detector = OriginalLocaleDetector()
            logger.debug("[Parsing] LocaleDetectorAdapter инициализирован")
        except Exception as e:
            raise LocaleDetectionError(
                message="Не удалось инициализировать LocaleDetector",
                component="LocaleDetectorAdapter",
                original_error=e
            )
    
    def detect(self, texts: List[str]) -> str:
        """
        Определяет локаль чека.
        
        Args:
            texts: Список текстовых строк чека
            
        Returns:
            Код локали (например, 'de_DE', 'pl_PL')
            
        Raises:
            LocaleDetectionError: Если произошла ошибка определения локали
        """
        try:
            logger.debug(f"[Parsing] Определение локали для {len(texts)} строк текста")
            
            locale_code = self._detector.detect(texts)
            
            logger.debug(f"[Parsing] Определена локаль: {locale_code}")
            return locale_code
            
        except Exception as e:
            raise LocaleDetectionError(
                message="Ошибка определения локали",
                component="LocaleDetectorAdapter",
                original_error=e
            )
