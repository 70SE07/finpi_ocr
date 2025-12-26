"""
Фабрика для создания компонентов домена Parsing.

Предоставляет удобные методы для создания и конфигурации
всех компонентов домена Parsing через единый интерфейс.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from ..domain.interfaces import (
    IReceiptParser, ILayoutProcessor, ILocaleDetector, 
    IMetadataExtractor, ISemanticExtractor, IParsingPipeline
)
from ..infrastructure.adapters.layout_processor_adapter import LayoutProcessorAdapter
from ..infrastructure.adapters.locale_detector_adapter import LocaleDetectorAdapter
from ..infrastructure.adapters.metadata_extractor_adapter import MetadataExtractorAdapter
from ..infrastructure.adapters.semantic_extractor_adapter import SemanticExtractorAdapter
from ..infrastructure.file_manager import ParsingFileManager
from .receipt_parser import ReceiptParser
from .parsing_pipeline import ParsingPipeline


class ParsingComponentFactory:
    """
    Фабрика для создания компонентов домена Parsing.
    
    Домен Parsing отвечает за:
    - Обработку layout сырых данных OCR
    - Определение локали
    - Извлечение метаданных
    - Семантическое извлечение товаров
    - Сохранение структурированных результатов
    """
    
    @staticmethod
    def create_layout_processor(use_result_processor: bool = True) -> ILayoutProcessor:
        """
        Создает процессор layout для домена Parsing.
        
        Args:
            use_result_processor: Использовать ResultProcessor вместо LayoutProcessor
            По умолчанию True, так как ResultProcessor лучше протестирован
            
        Returns:
            Процессор layout, реализующий интерфейс ILayoutProcessor
        """
        logger.debug("[Parsing] Создание процессора layout")
        return LayoutProcessorAdapter(use_result_processor=use_result_processor)
    
    @staticmethod
    def create_locale_detector() -> ILocaleDetector:
        """
        Создает детектор локали для домена Parsing.
        
        Returns:
            Детектор локали, реализующий интерфейс ILocaleDetector
        """
        logger.debug("[Parsing] Создание детектора локали")
        return LocaleDetectorAdapter()
    
    @staticmethod
    def create_metadata_extractor() -> IMetadataExtractor:
        """
        Создает экстрактор метаданных для домена Parsing.
        
        Returns:
            Экстрактор метаданных, реализующий интерфейс IMetadataExtractor
        """
        logger.debug("[Parsing] Создание экстрактора метаданных")
        return MetadataExtractorAdapter()
    
    @staticmethod
    def create_semantic_extractor() -> ISemanticExtractor:
        """
        Создает семантический экстрактор для домена Parsing.
        
        Returns:
            Семантический экстрактор, реализующий интерфейс ISemanticExtractor
        """
        logger.debug("[Parsing] Создание семантического экстрактора")
        return SemanticExtractorAdapter()
    
    @staticmethod
    def create_file_manager() -> ParsingFileManager:
        """
        Создает менеджер файлов для домена Parsing.
        
        Returns:
            Менеджер файлов домена Parsing
        """
        logger.debug("[Parsing] Создание менеджера файлов")
        return ParsingFileManager()
    
    @staticmethod
    def create_receipt_parser(
        layout_processor: Optional[ILayoutProcessor] = None,
        locale_detector: Optional[ILocaleDetector] = None,
        metadata_extractor: Optional[IMetadataExtractor] = None,
        semantic_extractor: Optional[ISemanticExtractor] = None,
        file_manager: Optional[ParsingFileManager] = None,
        save_intermediate: bool = False
    ) -> IReceiptParser:
        """
        Создает парсер чеков для домена Parsing.
        
        Args:
            layout_processor: Процессор layout (опционально)
            locale_detector: Детектор локали (опционально)
            metadata_extractor: Экстрактор метаданных (опционально)
            semantic_extractor: Семантический экстрактор (опционально)
            file_manager: Менеджер файлов (опционально)
            save_intermediate: Сохранять ли промежуточные результаты
            
        Returns:
            Парсер чеков, реализующий интерфейс IReceiptParser
        """
        logger.debug("[Parsing] Создание парсера чеков")
        
        # Создаем компоненты если они не предоставлены
        if layout_processor is None:
            layout_processor = ParsingComponentFactory.create_layout_processor()
        
        if locale_detector is None:
            locale_detector = ParsingComponentFactory.create_locale_detector()
        
        if metadata_extractor is None:
            metadata_extractor = ParsingComponentFactory.create_metadata_extractor()
        
        if semantic_extractor is None:
            semantic_extractor = ParsingComponentFactory.create_semantic_extractor()
        
        if file_manager is None:
            file_manager = ParsingComponentFactory.create_file_manager()
        
        return ReceiptParser(
            layout_processor=layout_processor,
            locale_detector=locale_detector,
            metadata_extractor=metadata_extractor,
            semantic_extractor=semantic_extractor,
            file_manager=file_manager,
            save_intermediate=save_intermediate
        )
    
    @staticmethod
    def create_parsing_pipeline(
        receipt_parser: Optional[IReceiptParser] = None,
        file_manager: Optional[ParsingFileManager] = None,
        output_dir: Optional[Path] = None,
        save_intermediate: bool = False
    ) -> IParsingPipeline:
        """
        Создает пайплайн parsing для домена Parsing.
        
        Args:
            receipt_parser: Парсер чеков (опционально)
            file_manager: Менеджер файлов (опционально)
            output_dir: Директория для сохранения структурированных результатов
            save_intermediate: Сохранять ли промежуточные результаты
            
        Returns:
            Пайплайн parsing, реализующий интерфейс IParsingPipeline
        """
        logger.debug("[Parsing] Создание пайплайна parsing")
        
        # Создаем компоненты если они не предоставлены
        if receipt_parser is None:
            receipt_parser = ParsingComponentFactory.create_receipt_parser(
                file_manager=file_manager,
                save_intermediate=save_intermediate
            )
        
        if file_manager is None:
            file_manager = ParsingComponentFactory.create_file_manager()
        
        # Определяем output_dir если не указан
        if output_dir is None:
            from config.settings import OUTPUT_DIR
            output_dir = OUTPUT_DIR
        
        return ParsingPipeline(
            receipt_parser=receipt_parser,
            file_manager=file_manager,
            output_dir=output_dir,
            save_intermediate=save_intermediate
        )
    
    @staticmethod
    def create_default_parsing_pipeline(save_intermediate: bool = False) -> IParsingPipeline:
        """
        Создает пайплайн parsing с настройками по умолчанию.
        
        Args:
            save_intermediate: Сохранять ли промежуточные результаты
            
        Returns:
            Полностью сконфигурированный пайплайн parsing
        """
        logger.info("[Parsing] Создание пайплайна parsing с настройками по умолчанию")
        
        # Создаем все компоненты с настройками по умолчанию
        file_manager = ParsingComponentFactory.create_file_manager()
        
        # Создаем парсер
        receipt_parser = ParsingComponentFactory.create_receipt_parser(
            file_manager=file_manager,
            save_intermediate=save_intermediate
        )
        
        # Определяем output_dir
        from config.settings import OUTPUT_DIR
        output_dir = OUTPUT_DIR
        
        # Создаем пайплайн
        return ParsingPipeline(
            receipt_parser=receipt_parser,
            file_manager=file_manager,
            output_dir=output_dir,
            save_intermediate=save_intermediate
        )
    
    @staticmethod
    def get_parsing_info() -> Dict[str, Any]:
        """
        Возвращает информацию о домене Parsing.
        
        Returns:
            Словарь с информацией о доступных компонентах и их возможностях
        """
        logger.debug("[Parsing] Получение информации о домене Parsing")
        
        return {
            "domain": "Parsing",
            "responsibility": "Обработка raw_ocr данных и извлечение структурированной информации",
            "input": "raw_ocr.json",
            "output": "structured_result.json",
            "components": {
                "layout_processor": "LayoutProcessorAdapter",
                "locale_detector": "LocaleDetectorAdapter",
                "metadata_extractor": "MetadataExtractorAdapter",
                "semantic_extractor": "SemanticExtractorAdapter",
                "file_manager": "ParsingFileManager",
                "receipt_parser": "ReceiptParser",
                "parsing_pipeline": "ParsingPipeline"
            },
            "capabilities": [
                "layout_processing",
                "locale_detection",
                "metadata_extraction",
                "semantic_extraction",
                "receipt_parsing",
                "file_management"
            ],
            "dependencies": ["Existing parsing modules"]
        }
