"""
Config Loader для конфигураций локалей парсинга.

ЦКП: Загрузка и мержинг YAML конфигов с поддержкой наследования.

Архитектурный принцип:
- Данные (ключевые слова, паттерны) в конфигах
- Логика (загрузка, мержинг) в коде
"""

import copy
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class ParsingConfig:
    """
    Конфигурация парсинга для одной локали.
    
    Содержит все необходимые данные для Stage 4 и Stage 5.
    """
    locale_code: str
    currency: str
    
    # Stage 4: Metadata
    total_keywords: List[str]
    
    # Stage 5: Semantic
    skip_keywords: List[str]
    discount_keywords: List[str]
    weight_patterns: List[str]
    tax_patterns: List[str]


class ConfigLoader:
    """
    Загрузчик конфигов локалей с поддержкой наследования.
    """
    
    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Args:
            locales_dir: Директория с конфигами (по умолчанию src/parsing/locales/)
        """
        if locales_dir is None:
            # Default: относительно файла config_loader.py
            current_file = Path(__file__)
            locales_dir = current_file.parent
        
        self.locales_dir = Path(locales_dir)
        self.base_config: Optional[Dict[str, Any]] = None
        self._cache: Dict[str, ParsingConfig] = {}
    
    def load(self, locale_code: str) -> ParsingConfig:
        """
        Загружает конфигурацию для локали.
        
        Args:
            locale_code: Код локали (например, "de_DE", "pl_PL")
            
        Returns:
            ParsingConfig: Загруженный конфиг
            
        Raises:
            FileNotFoundError: Если конфиг не найден
            ValueError: Если конфиг невалиден
        """
        # Проверяем кеш
        if locale_code in self._cache:
            return self._cache[locale_code]
        
        # 1. Загружаем базовый конфиг
        base_config = self._load_base_config()
        
        # 2. Загружаем конфиг локали
        locale_config = self._load_locale_config(locale_code)
        
        # 3. Мержим (locale перекрывает base)
        merged_config = self._merge_configs(base_config, locale_config)
        
        # 4. Парсим в ParsingConfig
        parsing_config = self._parse_config(merged_config, locale_code)
        
        # Кешируем
        self._cache[locale_code] = parsing_config
        
        logger.debug(
            f"[ConfigLoader] Загружен конфиг для {locale_code}: "
            f"{len(parsing_config.total_keywords)} total_keywords, "
            f"{len(parsing_config.skip_keywords)} skip_keywords"
        )
        
        return parsing_config
    
    def _load_base_config(self) -> Optional[Dict[str, Any]]:
        """Загружает базовый конфиг (base.yaml)."""
        if self.base_config is not None:
            base_file = self.locales_dir / "base.yaml"
            
            if not base_file.exists():
                logger.warning(f"[ConfigLoader] base.yaml не найден в {self.locales_dir}")
                self.base_config = {}
                return {}
            
            with open(base_file, 'r', encoding='utf-8') as f:
                self.base_config = yaml.safe_load(f)
        
        return self.base_config
    
    def _load_locale_config(self, locale_code: str) -> Dict[str, Any]:
        """Загружает конфиг специфичный для локали."""
        config_file = self.locales_dir / locale_code / "parsing.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"[ConfigLoader] Конфиг для {locale_code} не найден: {config_file}"
            )
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _merge_configs(
        self, 
        base: Optional[Dict[str, Any]], 
        locale: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Мержит базовый и локальный конфиг.
        
        Правила мержинга:
        1. locale перекрывает base
        2. Для списков — расширяет (base + locale)
        """
        import copy
        merged = copy.deepcopy(base or {})
        
        for key, locale_value in locale.items():
            # Простой тип (списки, скаляры) — заменяем
            if isinstance(locale_value, (list, str, int, float, bool)):
                merged[key] = locale_value
                continue
            
            # dict типа — мержинг списков
            if isinstance(locale_value, dict):
                # Поддержка extends (legacy формат)
                if "extends" in locale_value:
                    extends_key = locale_value["extends"]
                    base_value = merged.get(extends_key, [])
                    
                    if isinstance(base_value, list):
                        # Расширяем список
                        additional = locale_value.get("additional", [])
                        merged[key] = base_value + additional
                    else:
                        # Если base не список — берём только additional
                        merged[key] = locale_value.get("additional", [])
                else:
                    # Простое перекрытие (без extends)
                    merged[key] = locale_value
        
        return merged
    
    def _parse_config(self, config: Dict[str, Any], locale_code: str) -> ParsingConfig:
        """Парсит словарь конфига в ParsingConfig."""
        return ParsingConfig(
            locale_code=locale_code,
            currency=config.get("currency", "EUR"),
            total_keywords=config.get("total_keywords", ["total"]),
            skip_keywords=config.get("skip_keywords", []),
            discount_keywords=config.get("discount_keywords", []),
            weight_patterns=config.get("weight_patterns", []),
            tax_patterns=config.get("tax_patterns", []),
        )
    
    def clear_cache(self):
        """Очищает кеш конфигов."""
        self._cache.clear()
