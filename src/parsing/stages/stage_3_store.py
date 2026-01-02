"""
Stage 3: Store Detection

ЦКП: Определение магазина по тексту чека.

Входные данные: LayoutResult, LocaleResult
Выходные данные: StoreResult (название магазина, адрес)

Алгоритм:
1. Поиск известных брендов в первых N строках
2. Извлечение адреса (если найден)
3. Fallback на "UNKNOWN" если не найден
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from loguru import logger

from .stage_1_layout import LayoutResult
from .stage_2_locale import LocaleResult


# Известные бренды магазинов по локалям
KNOWN_STORES: Dict[str, Set[str]] = {
    "de_DE": {
        "lidl", "aldi", "aldi sud", "aldi nord", "rewe", "edeka", "kaufland",
        "netto", "penny", "dm", "rossmann", "muller", "hit", "real", "norma",
        "tegut", "globus", "famila", "marktkauf", "metro",
    },
    "pl_PL": {
        "biedronka", "lidl", "zabka", "żabka", "auchan", "carrefour", "tesco",
        "kaufland", "netto", "dino", "stokrotka", "lewiatan", "abc", "groszek",
        "polo market", "polomarket", "intermarche",
    },
    "es_ES": {
        "mercadona", "carrefour", "lidl", "aldi", "dia", "eroski", "hipercor",
        "el corte ingles", "consum", "bonarea", "simply", "alcampo",
    },
    "pt_PT": {
        "continente", "pingo doce", "lidl", "aldi", "minipreco", "intermarche",
        "jumbo", "auchan",
    },
    "cs_CZ": {
        "albert", "billa", "lidl", "kaufland", "tesco", "penny", "globus",
        "coop", "flop", "makro",
    },
}

# Сколько строк сканировать для поиска магазина
STORE_SCAN_LIMIT = 15


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
    
    ЦКП: Определение магазина по известным брендам.
    """
    
    def __init__(
        self,
        known_stores: Optional[Dict[str, Set[str]]] = None,
        scan_limit: int = STORE_SCAN_LIMIT,
    ):
        """
        Args:
            known_stores: Словарь {locale_code: {store_names}}
            scan_limit: Сколько строк сканировать
        """
        self.known_stores = known_stores or KNOWN_STORES
        self.scan_limit = scan_limit
    
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
        
        # Получаем известные бренды для локали
        locale_stores = self.known_stores.get(locale.locale_code, set())
        
        # Также проверяем глобальные бренды (Lidl, Aldi есть везде)
        global_stores = {"lidl", "aldi", "carrefour"}
        all_stores = locale_stores | global_stores
        
        # Сканируем первые N строк
        lines_to_scan = layout.lines[:self.scan_limit]
        
        store_name = None
        matched_line = -1
        confidence = 0.0
        
        for i, line in enumerate(lines_to_scan):
            line_lower = line.text.lower()
            
            for store in all_stores:
                if store in line_lower:
                    # Нормализуем название (первая буква заглавная)
                    store_name = store.replace(' ', '').lower()
                    matched_line = i
                    confidence = 1.0 if store in locale_stores else 0.8
                    
                    logger.info(f"[Stage 3: Store] Найден магазин: {store_name} (строка {i})")
                    break
            
            if store_name:
                break
        
        # Пробуем извлечь адрес (строки после названия магазина)
        store_address = None
        if matched_line >= 0 and matched_line + 1 < len(lines_to_scan):
            # Адрес обычно в следующих 2-3 строках
            address_lines = []
            for j in range(matched_line + 1, min(matched_line + 4, len(lines_to_scan))):
                line_text = layout.lines[j].text
                # Пропускаем строки с ценами или итогами
                if self._looks_like_address(line_text):
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
    
    def _looks_like_address(self, text: str) -> bool:
        """Проверяет, похожа ли строка на адрес."""
        text_lower = text.lower()
        
        # Признаки адреса
        address_hints = [
            "str.", "straße", "strasse", "weg", "platz", "allee",  # DE
            "ul.", "ulica", "al.", "aleja", "pl.",  # PL
            "c/", "calle", "av.", "avda", "plaza",  # ES
            "rua", "av.", "avenida", "praça",  # PT
        ]
        
        # Признаки НЕ адреса
        non_address_hints = [
            "summe", "total", "eur", "pln", "€", "zł",
            "mwst", "ust", "vat", "ptu",
        ]
        
        # Проверяем
        for hint in non_address_hints:
            if hint in text_lower:
                return False
        
        for hint in address_hints:
            if hint in text_lower:
                return True
        
        # Если короткая строка с цифрами — возможно это индекс/номер дома
        if len(text) < 50 and any(c.isdigit() for c in text):
            return True
        
        return False
