"""
Адаптер для MetadataExtractor, реализующий интерфейс IMetadataExtractor (домен Parsing).
"""

from typing import List, Dict, Any
from loguru import logger

from ...domain.interfaces import IMetadataExtractor
from ...domain.exceptions import MetadataExtractionError
from ...metadata.metadata_extractor import MetadataExtractor as OriginalMetadataExtractor
from ...locales.locale_config import LocaleConfig


class MetadataExtractorAdapter(IMetadataExtractor):
    """
    Адаптер для MetadataExtractor (домен Parsing).
    
    Реализует интерфейс IMetadataExtractor, делегируя вызовы оригинальному MetadataExtractor.
    """
    
    def __init__(self):
        """Инициализация адаптера."""
        try:
            self._extractor = OriginalMetadataExtractor()
            logger.debug("[Parsing] MetadataExtractorAdapter инициализирован")
        except Exception as e:
            raise MetadataExtractionError(
                message="Не удалось инициализировать MetadataExtractor",
                component="MetadataExtractorAdapter",
                original_error=e
            )
    
    def extract(self, texts: List[str], locale_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает метаданные из чека.
        
        Args:
            texts: Список текстовых строк чека
            locale_config: Конфигурация локали (в виде словаря)
            
        Returns:
            Метаданные чека (магазин, дата, сумма и т.д.)
            
        Raises:
            MetadataExtractionError: Если произошла ошибка извлечения
        """
        try:
            logger.debug(f"[Parsing] Извлечение метаданных для {len(texts)} строк")
            
            # Конвертируем словарь конфигурации в объект LocaleConfig
            locale_obj = self._convert_to_locale_config(locale_config)
            
            # Вызываем оригинальный метод
            result = self._extractor.process(texts, locale_config=locale_obj)
            
            # Конвертируем результат в словарь
            if hasattr(result, 'to_dict'):
                metadata_dict = result.to_dict()
            elif hasattr(result, '__dict__'):
                metadata_dict = result.__dict__
            else:
                metadata_dict = {"raw_result": result}
            
            logger.debug(f"[Parsing] Извлечены метаданные: {list(metadata_dict.keys())}")
            return metadata_dict
            
        except Exception as e:
            raise MetadataExtractionError(
                message="Ошибка извлечения метаданных",
                component="MetadataExtractorAdapter",
                original_error=e
            )
    
    def _convert_to_locale_config(self, locale_config_dict: Dict[str, Any]) -> LocaleConfig:
        """
        Конвертирует словарь в объект LocaleConfig.
        
        Args:
            locale_config_dict: Словарь с конфигурацией локали
            
        Returns:
            Объект LocaleConfig
        """
        try:
            # Пытаемся создать LocaleConfig из словаря
            if isinstance(locale_config_dict, LocaleConfig):
                return locale_config_dict
            
            # Используем метод from_dict если он существует
            if hasattr(LocaleConfig, 'from_dict'):
                return LocaleConfig.from_dict(locale_config_dict)
            
            # Извлекаем region из code (например, 'de_DE' -> 'DE')
            code = locale_config_dict.get('code', '')
            region = code.split('_')[-1] if '_' in code else code.upper()
            
            # Создаем объект напрямую с правильными параметрами
            return LocaleConfig(
                code=code,
                name=locale_config_dict.get('name', ''),
                language=locale_config_dict.get('language', ''),
                region=region
            )
            
        except Exception as e:
            logger.warning(f"[Parsing] Не удалось конвертировать конфигурацию локали: {e}")
            # Возвращаем дефолтную конфигурацию
            return LocaleConfig(
                code=locale_config_dict.get('code', 'unknown'),
                name=locale_config_dict.get('name', 'Unknown'),
                language='en',
                region='US'
            )
