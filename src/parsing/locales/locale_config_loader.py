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
    
    def load(self, locale_code: str) -> LocaleConfig:
        """
        Загружает конфигурацию для указанной локали с валидацией.
        
        Args:
            locale_code: Код локали (de_DE, pl_PL, ...)
            
        Returns:
            LocaleConfig: Валидированная конфигурация
            
        Raises:
            FileNotFoundError: Если конфиг не найден
            ValidationError: Если конфигурация невалидна (Pydantic)
        """
        config_path = self.locales_dir / locale_code / "config.yaml"
        
        if not config_path.exists():
            available = self._get_available_locales()
            raise FileNotFoundError(
                f"Конфигурация для локали '{locale_code}' не найдена: {config_path}\n"
                f"Доступные локали: {available}\n"
                f"Используйте одну из доступных локалей или создайте конфигурацию."
            )
        
        logger.debug(f"[LocaleConfigLoader] Загрузка конфига для {locale_code}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        try:
            return self._parse_and_validate(data, locale_code)
        except ValidationError as e:
            logger.error(f"[LocaleConfigLoader] Ошибка валидации конфигурации для {locale_code}")
            logger.error(f"[LocaleConfigLoader] Ошибки Pydantic:\n{e}")
            raise ValueError(
                f"Конфигурация для локали '{locale_code}' невалидна.\n"
                f"Пожалуйста, исправьте ошибки в {config_path}:\n{e}"
            ) from e
    
    def _parse_and_validate(self, data: dict, locale_code: str) -> LocaleConfig:
        """
        Парсит YAML и валидирует через Pydantic.
        
        Args:
            data: Словарь из YAML файла
            locale_code: Код локали (для автозаполнения)
            
        Returns:
            Валидированный LocaleConfig
        """
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
            raise
    
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
