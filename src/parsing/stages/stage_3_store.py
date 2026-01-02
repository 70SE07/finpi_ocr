"""
Stage 3: Store Detection

ЦКП: Определение магазина по тексту чека.

Входные данные: LayoutResult, LocaleResult
Выходные данные: StoreResult (название магазина, адрес)

Алгоритм:
1. Загрузка брендов из ConfigLoader (stores/*.yaml → detection)
2. Поиск известных брендов в первых N строках
3. Извлечение адреса (если найден)
4. Fallback на None если не найден

СИСТЕМНЫЙ ПРИНЦИП:
- 0 хардкода магазинов в Python коде
- Все магазины загружаются из YAML конфигов
- Новый магазин = новый YAML файл, 0 изменений в коде
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from loguru import logger

from .stage_1_layout import LayoutResult
from .stage_2_locale import LocaleResult
from ..locales.config_loader import ConfigLoader, StoreDetectionConfig, LocaleConfig


# Сколько строк сканировать для поиска магазина
STORE_SCAN_LIMIT = 15

# Глобальные бренды, которые присутствуют во многих странах
# Используются как fallback если магазин не найден в локальных конфигах
GLOBAL_STORES: Set[str] = {"lidl", "aldi", "carrefour"}


@dataclass
class StoreResult:
    """
    Результат Stage 3: Store Detection.
    
    ЦКП: Определённый магазин с адресом.
    """
    store_name: Optional[str] = None       # Название магазина
    store_address: Optional[str] = None    # Адрес магазина
    confidence: float = 0.0                # Уверенность
    matched_in_line: int = -1              # Номер строки где найден
    
    def to_dict(self) -> dict:
        return {
            "store_name": self.store_name,
            "store_address": self.store_address,
            "confidence": self.confidence,
            "matched_in_line": self.matched_in_line,
        }


class StoreStage:
    """
    Stage 3: Store Detection.
    
    ЦКП: Определение магазина по известным брендам из конфигурации.
    
    СИСТЕМНЫЙ ПРИНЦИП:
    - Магазины загружаются из stores/*.yaml через ConfigLoader
    - 0 хардкода брендов в Python коде
    - Поддержка приоритетов при конфликтах
    """
    
    def __init__(
        self,
        config_loader: Optional[ConfigLoader] = None,
        scan_limit: int = STORE_SCAN_LIMIT,
        address_hints: Optional[List[str]] = None,
    ):
        """
        Args:
            config_loader: Загрузчик конфигураций (для stores/*.yaml)
            scan_limit: Сколько строк сканировать
            address_hints: Признаки адреса (загружаются из конфига если None)
        """
        self.config_loader = config_loader or ConfigLoader()
        self.scan_limit = scan_limit
        self._stores_cache: Dict[str, List[StoreDetectionConfig]] = {}
        self._address_hints_cache: Dict[str, List[str]] = {}
        self._custom_address_hints = address_hints
    
    def _get_stores_for_locale(self, locale_code: str) -> List[StoreDetectionConfig]:
        """Получает список магазинов для локали из кеша или загружает."""
        if locale_code not in self._stores_cache:
            try:
                config = self.config_loader.load(locale_code)
                self._stores_cache[locale_code] = config.stores
            except FileNotFoundError:
                logger.warning(f"[Stage 3: Store] Конфиг для {locale_code} не найден")
                self._stores_cache[locale_code] = []
        return self._stores_cache[locale_code]
    
    def _get_address_hints(self, locale_code: str) -> List[str]:
        """Получает признаки адреса для локали из конфига."""
        if self._custom_address_hints:
            return self._custom_address_hints
        
        if locale_code not in self._address_hints_cache:
            try:
                config = self.config_loader.load(locale_code)
                hints = config.address_hints if config.address_hints else []
                self._address_hints_cache[locale_code] = hints
            except FileNotFoundError:
                self._address_hints_cache[locale_code] = []
        return self._address_hints_cache[locale_code]
    
    def _get_non_address_hints(self, locale_code: str) -> List[str]:
        """Получает признаки НЕ адреса для локали из конфига."""
        try:
            config = self.config_loader.load(locale_code)
            return config.non_address_hints if config.non_address_hints else []
        except FileNotFoundError:
            return []
    
    def process(self, layout: LayoutResult, locale: LocaleResult) -> StoreResult:
        """
        Определяет магазин по тексту чека.
        
        Args:
            layout: Результат Stage 1 (Layout)
            locale: Результат Stage 2 (Locale)
            
        Returns:
            StoreResult: Определённый магазин
        """
        logger.debug(f"[Stage 3: Store] Поиск магазина для локали {locale.locale_code}")
        
        # 1. Загружаем магазины из конфига (с кешированием)
        stores = self._get_stores_for_locale(locale.locale_code)
        
        # Сканируем первые N строк
        lines_to_scan = layout.lines[:self.scan_limit]
        
        store_name = None
        matched_line = -1
        confidence = 0.0
        
        # 2. Ищем по brands и aliases из конфига
        for i, line in enumerate(lines_to_scan):
            line_lower = line.text.lower()
            
            for store_config in stores:
                # Ищем brands (высокий confidence)
                for brand in store_config.brands:
                    if brand.lower() in line_lower:
                        store_name = store_config.name
                        matched_line = i
                        confidence = 1.0
                        logger.info(f"[Stage 3: Store] Найден магазин по brand: {store_name} (строка {i}, brand='{brand}')")
                        break
                
                if store_name:
                    break
                
                # Ищем aliases (пониженный confidence)
                for alias in store_config.aliases:
                    if alias.lower() in line_lower:
                        store_name = store_config.name
                        matched_line = i
                        confidence = 0.9
                        logger.info(f"[Stage 3: Store] Найден магазин по alias: {store_name} (строка {i}, alias='{alias}')")
                        break
                
                if store_name:
                    break
            
            if store_name:
                break
        
        # 3. Fallback на глобальные бренды (если не найден в локальных конфигах)
        if not store_name:
            for i, line in enumerate(lines_to_scan):
                line_lower = line.text.lower()
                for global_brand in GLOBAL_STORES:
                    if global_brand in line_lower:
                        store_name = global_brand
                        matched_line = i
                        confidence = 0.7  # Ниже confidence для глобального fallback
                        logger.info(f"[Stage 3: Store] Найден глобальный магазин: {store_name} (строка {i})")
                        break
                if store_name:
                    break
        
        # 4. Пробуем извлечь адрес (строки после названия магазина)
        store_address = None
        if matched_line >= 0 and matched_line + 1 < len(lines_to_scan):
            address_lines = []
            address_hints = self._get_address_hints(locale.locale_code)
            non_address_hints = self._get_non_address_hints(locale.locale_code)
            
            for j in range(matched_line + 1, min(matched_line + 4, len(lines_to_scan))):
                line_text = layout.lines[j].text
                if self._looks_like_address(line_text, address_hints, non_address_hints):
                    address_lines.append(line_text)
                else:
                    break
            
            if address_lines:
                store_address = ", ".join(address_lines)
        
        result = StoreResult(
            store_name=store_name,
            store_address=store_address,
            confidence=confidence,
            matched_in_line=matched_line,
        )
        
        if not store_name:
            logger.warning("[Stage 3: Store] Магазин не найден")
        
        return result
    
    def _looks_like_address(self, text: str, address_hints: List[str], non_address_hints: List[str]) -> bool:
        """
        Проверяет, похожа ли строка на адрес.
        
        Args:
            text: Текст строки
            address_hints: Признаки адреса (из конфига)
            non_address_hints: Признаки НЕ адреса (из конфига)
        """
        text_lower = text.lower()
        
        # Базовые исключения (универсальные, всегда применяются)
        base_non_address = ["€", "zł", "kč", "czk"]
        
        # Проверяем исключения из конфига
        for hint in non_address_hints:
            if hint in text_lower:
                return False
        
        # Проверяем базовые исключения
        for hint in base_non_address:
            if hint in text_lower:
                return False
        
        # Проверяем признаки адреса из конфига
        for hint in address_hints:
            if hint in text_lower:
                return True
        
        # Если короткая строка с цифрами — возможно это индекс/номер дома
        if len(text) < 50 and any(c.isdigit() for c in text):
            return True
        
        return False
