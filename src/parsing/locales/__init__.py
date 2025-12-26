"""
Система локалей для домена Parsing.

Содержит:
- LocaleConfig: DTO конфигурации локали (с Pydantic валидацией)
- LocaleConfigLoader: Загрузчик конфигураций из YAML файлов
- LocaleDetector: Автоматическое определение локали по тексту чека
- LocaleRegistry: Централизованный реестр всех доступных локалей
"""

from .locale_config import (
    LocaleConfig, CurrencyConfig, DateConfig, 
    PatternsConfig, ExtractorConfig
)
from .locale_config_loader import LocaleConfigLoader
from .locale_detector import LocaleDetector
from .locale_registry import LocaleRegistry

__all__ = [
    # Конфигурация локали
    "LocaleConfig",
    "CurrencyConfig",
    "DateConfig",
    "PatternsConfig",
    "ExtractorConfig",
    
    # Загрузчик конфигураций
    "LocaleConfigLoader",
    
    # Детектор локали
    "LocaleDetector",
    
    # Реестр локалей
    "LocaleRegistry",
]
