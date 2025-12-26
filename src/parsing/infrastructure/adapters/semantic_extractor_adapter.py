"""
Адаптер для SemanticExtractor, реализующий интерфейс ISemanticExtractor (домен Parsing).
"""

from typing import List, Dict, Any
from loguru import logger

from ...domain.interfaces import ISemanticExtractor
from ...domain.exceptions import SemanticExtractionError
from ...extraction.semantic_extractor import SemanticExtractor as OriginalSemanticExtractor
from ...locales.locale_config import LocaleConfig
from ...dto import TextBlock, BoundingBox


class SemanticExtractorAdapter(ISemanticExtractor):
    """
    Адаптер для SemanticExtractor (домен Parsing).
    
    Реализует интерфейс ISemanticExtractor, делегируя вызовы оригинальному SemanticExtractor.
    """
    
    def __init__(self):
        """Инициализация адаптера."""
        try:
            self._extractor = OriginalSemanticExtractor()
            logger.debug("[Parsing] SemanticExtractorAdapter инициализирован")
        except Exception as e:
            raise SemanticExtractionError(
                message="Не удалось инициализировать SemanticExtractor",
                component="SemanticExtractorAdapter",
                original_error=e
            )
    
    def extract(self, lines: List[Dict[str, Any]], locale_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Извлекает товары из строк чека.
        
        Args:
            lines: Список строк чека (в виде словарей)
            locale_config: Конфигурация локали
            
        Returns:
            Список товаров с деталями
            
        Raises:
            SemanticExtractionError: Если произошла ошибка извлечения
        """
        try:
            logger.debug(f"[Parsing] Семантическое извлечение для {len(lines)} строк")
            
            # Конвертируем словари в TextBlock объекты
            text_blocks = self._convert_to_text_blocks(lines)
            
            # Конвертируем словарь конфигурации в объект LocaleConfig
            locale_obj = self._convert_to_locale_config(locale_config)
            
            # Устанавливаем конфигурацию локали в экстрактор
            self._extractor.locale_config = locale_obj
            
            # Вызываем оригинальный метод
            result = self._extractor.process(text_blocks)
            
            # Извлекаем товары из результата
            items = result.get('items', [])
            
            logger.debug(f"[Parsing] Извлечено товаров: {len(items)}")
            return items
            
        except Exception as e:
            raise SemanticExtractionError(
                message="Ошибка семантического извлечения",
                component="SemanticExtractorAdapter",
                original_error=e
            )
    
    def _convert_to_text_blocks(self, lines: List[Dict[str, Any]]) -> List[TextBlock]:
        """
        Конвертирует словари в объекты TextBlock.
        
        Args:
            lines: Список строк в виде словарей
            
        Returns:
            Список объектов TextBlock
        """
        text_blocks = []
        
        for line in lines:
            bbox = None
            if line.get('bounding_box'):
                bbox_data = line['bounding_box']
                bbox = BoundingBox(
                    x_min=bbox_data.get('x_min', 0),
                    y_min=bbox_data.get('y_min', 0),
                    x_max=bbox_data.get('x_max', 0),
                    y_max=bbox_data.get('y_max', 0)
                )
            
            text_block = TextBlock(
                text=line.get('text', ''),
                confidence=line.get('confidence', 0.0),
                bounding_box=bbox,
                block_type=line.get('block_type', 'TEXT')
            )
            text_blocks.append(text_block)
        
        return text_blocks
    
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
