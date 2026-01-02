"""
Загрузчик конфигурации локали из YAML файлов.

Структура директорий:
locales/
  ├── de_DE/
  │   ├── config.yaml
  │   └── examples/
  ├── pl_PL/
  │   ├── config.yaml
  │   └── examples/
  
Использует Pydantic для валидации структуры конфигурации.
"""

import yaml
from pathlib import Path
from typing import Optional
from loguru import logger
from pydantic import ValidationError

from .locale_config import (
    LocaleConfig, CurrencyConfig, DateConfig, 
    PatternsConfig, ExtractorConfig
)


class LocaleConfigLoader:
    """Загружает конфигурацию локали из YAML файлов с валидацией через Pydantic."""
    
    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Args:
            locales_dir: Директория с конфигами (по умолчанию locales/ в src/parsing/)
        """
        if locales_dir is None:
            # locales теперь находится в src/parsing/locales/
            self.locales_dir = Path(__file__).parent
        else:
            self.locales_dir = Path(locales_dir)
    
    def load(self, locale_code: str, store_name: Optional[str] = None) -> LocaleConfig:
        """
        Загружает конфигурацию для указанной локали и магазина.
        
        Args:
            locale_code: Код локали (de_DE, pl_PL, ...)
            store_name: Имя магазина (опционально)
        """
        # Загружаем базовую конфигурацию локали
        config_path = self.locales_dir / locale_code / "config.yaml"
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # Если указан магазин, загружаем его конфиг и мержим с locale config
        if store_name:
            store_config_path = self.locales_dir / locale_code / "stores" / f"{store_name}.yaml"
            
            if store_config_path.exists():
                with open(store_config_path, "r", encoding="utf-8") as f:
                    store_data = yaml.safe_load(f)
                
                # Мержим store config в locale config
                data = self._merge_configs(data, store_data)
                logger.debug(f"[LocaleConfigLoader] Loaded store config: {store_name}")
            else:
                logger.warning(
                    f"[LocaleConfigLoader] Store config not found: {store_config_path}"
                )
        
        return self._parse_and_validate(data, locale_code)
    
    def _merge_configs(self, base_config: dict, override_config: dict) -> dict:
        """
        Мержит store config в locale config.
        
        Store config может override следующие секции:
        - currency (decimal_separator, thousands_separator)
        - patterns (total_keywords, discount_keywords, noise_keywords)
        - extractors (store_detection, total_detection, semantic_extraction)
        """
        merged = base_config.copy()
        
        # Merge currency
        if "currency" in override_config:
            if "currency" not in merged:
                merged["currency"] = {}
            for key, value in override_config["currency"].items():
                merged["currency"][key] = value
        
        # Merge patterns
        if "patterns" in override_config:
            if "patterns" not in merged:
                merged["patterns"] = {}
            for key, value in override_config["patterns"].items():
                if key not in merged["patterns"]:
                    merged["patterns"][key] = []
                merged["patterns"][key].extend(value)
        
        # Merge extractors
        if "extractors" in override_config:
            if "extractors" not in merged:
                merged["extractors"] = {}
            for key, value in override_config["extractors"].items():
                merged["extractors"][key] = value
        
        return merged
    
    def _parse_and_validate(self, data: dict, locale_code: str) -> LocaleConfig:
        """
        Парсит YAML и валидирует через Pydantic.
        
        Args:
            data: Словарь из YAML файла
            locale_code: Код локали (для автозаполнения)
            
        Returns:
            Валидированный LocaleConfig
        """
        # Проверка обязательных полей
        required_fields = ["locale", "currency", "patterns"]
        for field in required_fields:
            if field not in data:
                raise ValueError(
                    f"Required field '{field}' is missing in locale config for {locale_code}"
                )
        
        # Проверка обязательных полей в patterns
        if "patterns" in data:
            patterns = data["patterns"]
            required_pattern_fields = ["total_keywords", "discount_keywords", "noise_keywords"]
            for field in required_pattern_fields:
                if field not in patterns:
                    raise ValueError(
                        f"Required field 'patterns.{field}' is missing in locale config for {locale_code}"
                    )
        
        # Базовые поля локали
        locale_data = data.get("locale", {})
        if not locale_data:
            raise ValueError("Раздел 'locale' обязателен в конфигурации")
        
        # Подготовка данных для Pydantic модели
        config_dict = {
            "code": locale_code,  # Используем имя папки как код
            "name": locale_data.get("name", locale_code),
            "language": locale_data.get("language", "en"),
            "region": locale_data.get("region", locale_code.split("_")[1] if "_" in locale_code else ""),
            "rtl": locale_data.get("rtl", False),
        }
        
        # Currency config
        currency_data = data.get("currency")
        if currency_data:
            config_dict["currency"] = {
                "code": currency_data.get("code", "EUR"),
                "symbol": currency_data.get("symbol", "€"),
                "decimal_separator": currency_data.get("decimal_separator", ","),
                "thousands_separator": currency_data.get("thousands_separator", "."),
                "symbol_position": currency_data.get("symbol_position", "after"),
                "format": currency_data.get("format", "1.234,56")
            }
        
        # Date config
        date_data = data.get("date_formats")
        if date_data:
            if isinstance(date_data, list):
                config_dict["date"] = {"formats": date_data}
            else:
                config_dict["date"] = {"formats": date_data.get("formats", ["DD.MM.YYYY"])}
        
        # Patterns config
        patterns_data = data.get("patterns")
        if patterns_data:
            config_dict["patterns"] = {
                "total_keywords": patterns_data.get("total_keywords", []),
                "discount_keywords": patterns_data.get("discount_keywords", []),
                "noise_keywords": patterns_data.get("noise_keywords", [])
            }
        
        # Extractors config
        extractors_data = data.get("extractors")
        if extractors_data:
            config_dict["extractors"] = {
                "store_detection": extractors_data.get("store_detection", {}),
                "total_detection": extractors_data.get("total_detection", {})
            }
        
        # Валидация через Pydantic
        try:
            return LocaleConfig(**config_dict)
        except ValidationError as e:
            # Re-raise для понятных сообщений об ошибках
            raise ValueError(
                f"Конфигурация для локали '{locale_code}' невалидна.\n"
                f"Пожалуйста, исправьте ошибки в {self.locales_dir / locale_code / 'config.yaml'}:\n{e}"
            ) from e
    def _get_available_locales(self) -> list:
        """Возвращает список доступных локалей."""
        if not self.locales_dir.exists():
            return []
        
        locales = []
        for item in self.locales_dir.iterdir():
            # Пропускаем __pycache__ и файлы
            if item.name.startswith("_") or not item.is_dir():
                continue
            # Проверяем наличие config.yaml
            if (item / "config.yaml").exists():
                locales.append(item.name)
        
        return sorted(locales)
    
    def list_available(self) -> list:
        """Возвращает список доступных локалей (для логирования)."""
        available = self._get_available_locales()
        logger.info(f"[LocaleConfigLoader] Доступные локали: {available}")
        return available
