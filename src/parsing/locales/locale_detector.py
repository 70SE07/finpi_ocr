"""
Детектор локали по тексту чека.

Стратегии:
1. Поиск валютного символа (самый надежный)
2. Поиск ключевых слов (total, summe, сумма)
3. Поиск бренда магазина (если есть база)
"""

from typing import List, Optional, Dict, Tuple
from loguru import logger

from .locale_config_loader import LocaleConfigLoader
from .locale_config import LocaleConfig

from config.settings import DEFAULT_LOCALE, FALLBACK_LOCALE


class LocaleDetector:
    """
    Автоматически определяет локаль чека по тексту.
    
    Использует многоуровневую стратегию:
    1. Currency detection (наиболее надежно)
    2. Keyword detection (total, summe, сумма)
    3. Store brand detection (если есть база)
    """
    
    def __init__(self, config_loader: Optional[LocaleConfigLoader] = None):
        """
        Args:
            config_loader: Загрузчик конфигов (если None - создастся дефолтный)
        """
        self.config_loader = config_loader or LocaleConfigLoader()
        
        # Кэш загруженных конфигов для быстрой детекции
        self._config_cache: Dict[str, LocaleConfig] = {}
    
    def detect(self, texts: List[str]) -> str:
        """
        Определяет локаль по списку текстовых строк.
        
        Args:
            texts: Список строк чека (Layout)
            
        Returns:
            str: Код локали (de_DE, pl_PL, ...)
        """
        full_text = " ".join(texts).lower()
        
        logger.debug(f"[LocaleDetector] Анализ текста для определения локали...")
        
        # Стратегия 1: Currency detection
        locale = self._detect_by_currency(full_text)
        if locale:
            logger.info(f"[LocaleDetector] Локаль определена по валюте: {locale}")
            return locale
        
        # Стратегия 2: Keyword detection
        locale = self._detect_by_keywords(full_text)
        if locale:
            logger.info(f"[LocaleDetector] Локаль определена по ключевым словам: {locale}")
            return locale
        
        # Стратегия 3: Store brand detection (будет позже)
        # locale = self._detect_by_store_brand(texts)
        
        # Fallback: дефолтная локаль из настроек
        logger.warning(
            f"[LocaleDetector] Не удалось определить локаль автоматически. "
            f"Используем дефолтную: {DEFAULT_LOCALE}"
        )
        return self._get_fallback_locale(DEFAULT_LOCALE)
    
    def _detect_by_currency(self, text: str) -> Optional[str]:
        """
        Детекция локали по валютному символу.
        
        Примеры:
        - € → EUR → de_DE, at_AT, fr_FR (нужна эвристика)
        - zł → PLN → pl_PL
        - ฿ → THB → th_TH
        - ₸ → KZT → kz_KZ
        """
        # Карта валютного символа к коду локали
        currency_to_locale = {
            "€": ["de_DE", "fr_FR", "es_ES", "it_IT", "pt_PT"],
            "zł": ["pl_PL"],
            "z": ["pl_PL"],  # Иногда OCR распознаёт как "z"
            "฿": ["th_TH"],
            "₸": ["kz_KZ"],
            "$": ["en_US"],
            "£": ["en_GB"],
        }
        
        for symbol, locales in currency_to_locale.items():
            if symbol in text:
                # Если несколько локалей используют одну валюту (€),
                # используем эвристику по ключевым словам
                if len(locales) == 1:
                    return locales[0]
                else:
                    # EUR: пробуем уточнить по ключевым словам
                    return self._disambiguate_euro(text, locales)
        
        return None
    
    def _disambiguate_euro(self, text: str, euro_locales: List[str]) -> Optional[str]:
        """
        Уточнение локали для Euro-zone стран.
        
        Проверяет ключевые слова для de_DE:
        - "gesamtbetrag", "summe", "zu zahlen" → de_DE
        """
        german_keywords = ["gesamtbetrag", "summe", "zu zahlen", "belegsumme", "endbetrag"]
        french_keywords = ["total", "tva"]
        polish_keywords = ["suma", "razem"]
        
        # Проверяем немецкие ключевые слова
        for kw in german_keywords:
            if kw in text:
                return "de_DE"
        
        # Проверяем французские
        for kw in french_keywords:
            if kw in text:
                return "fr_FR"
        
        # Проверяем польские
        for kw in polish_keywords:
            if kw in text:
                return "pl_PL"
        
        # Если не определили - дефолт
        return "de_DE"
    
    def _detect_by_keywords(self, text: str) -> Optional[str]:
        """
        Детекция локали по ключевым словам total/sum.
        
        Примеры:
        - "gesamtbetrag", "summe" → de_DE
        - "suma", "razem" → pl_PL
        - "сумма", "итого" → ru_RU
        """
        keyword_to_locale = {
            "gesamtbetrag": "de_DE",
            "summe": "de_DE",
            "zu zahlen": "de_DE",
            "belegsumme": "de_DE",
            "endbetrag": "de_DE",
            "rechnungsbetrag": "de_DE",
            
            "suma": "pl_PL",
            "razem": "pl_PL",
            
            "total": "en_US",  # Может быть и в DE чеках
            "итого": "ru_RU",
            "сумма": "ru_RU",
        }
        
        for keyword, locale in keyword_to_locale.items():
            if keyword in text:
                return locale
        
        return None
    
    def _get_locale_config(self, locale_code: str) -> LocaleConfig:
        """Загружает конфиг из кэша или с диска."""
        if locale_code not in self._config_cache:
            self._config_cache[locale_code] = self.config_loader.load(locale_code)
        return self._config_cache[locale_code]

    def _get_fallback_locale(self, default_locale: str) -> str:
        """
        Возвращает доступную локаль для фолбэка.
        
        Проверяет доступность дефолтной локали. Если недоступна,
        использует FALLBACK_LOCALE (en_US).
        
        Args:
            default_locale: Дефолтная локаль из настроек
            
        Returns:
            str: Код доступной локали
        """
        # Проверяем доступность дефолтной локали
        available_locales = self.config_loader.list_available()
        
        if default_locale in available_locales:
            logger.debug(f"[LocaleDetector] Дефолтная локаль {default_locale} доступна")
            return default_locale
        
        # Если дефолтная недоступна, проверяем фолбэк
        if FALLBACK_LOCALE in available_locales:
            logger.warning(
                f"[LocaleDetector] Дефолтная локаль {default_locale} недоступна. "
                f"Используем фолбэк: {FALLBACK_LOCALE}"
            )
            logger.warning(
                f"[LocaleDetector] Пожалуйста, создайте конфигурацию для {default_locale} "
                f"или измените DEFAULT_LOCALE в config/settings.py"
            )
            return FALLBACK_LOCALE
        
        # Если и фолбэк недоступен, используем первую доступную локаль
        if available_locales:
            first_locale = available_locales[0]
            logger.error(
                f"[LocaleDetector] И дефолтная локаль {default_locale} "
                f"и фолбэк {FALLBACK_LOCALE} недоступны! "
                f"Используем первую доступную: {first_locale}"
            )
            return first_locale
        
        # Если нет ни одной локали - критическая ошибка
        logger.error(
            f"[LocaleDetector] КРИТИЧЕСКАЯ ОШИБКА: "
            f"Нет ни одной конфигурации локали! "
            f"Создайте хотя бы одну конфигурацию в src/parsing/locales/"
        )
        raise ValueError(
            "Нет доступных конфигураций локалей. "
            "Создайте хотя бы одну конфигурацию в src/parsing/locales/"
        )


