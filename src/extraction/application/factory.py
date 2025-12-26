"""
Фабрика для создания компонентов домена Extraction.

Предоставляет удобные методы для создания и конфигурации
всех компонентов домена Extraction через единый интерфейс.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from ..domain.interfaces import IOCRProvider, IImagePreprocessor, IExtractionPipeline
from ..infrastructure.adapters.google_vision_adapter import GoogleVisionOCRAdapter
from ..infrastructure.adapters.image_preprocessor_adapter import ImagePreprocessorAdapter
from ..infrastructure.file_manager import ExtractionFileManager
from .extraction_pipeline import ExtractionPipeline


class ExtractionComponentFactory:
    """
    Фабрика для создания компонентов домена Extraction.
    
    Домен Extraction отвечает за:
    - Preprocessing изображений
    - OCR распознавание текста
    - Сохранение сырых результатов в raw_ocr.json
    """
    
    @staticmethod
    def create_ocr_provider(credentials_path: Optional[str] = None) -> IOCRProvider:
        """
        Создает провайдер OCR для домена Extraction.
        
        Args:
            credentials_path: Путь к credentials файлу Google Cloud
            
        Returns:
            Провайдер OCR, реализующий интерфейс IOCRProvider
        """
        logger.debug("[Extraction] Создание OCR провайдера")
        return GoogleVisionOCRAdapter(credentials_path)
    
    @staticmethod
    def create_image_preprocessor() -> IImagePreprocessor:
        """
        Создает препроцессор изображений для домена Extraction.
        
        Returns:
            Препроцессор изображений, реализующий интерфейс IImagePreprocessor
        """
        logger.debug("[Extraction] Создание препроцессора изображений")
        return ImagePreprocessorAdapter()
    
    @staticmethod
    def create_file_manager() -> ExtractionFileManager:
        """
        Создает менеджер файлов для домена Extraction.
        
        Returns:
            Менеджер файлов домена Extraction
        """
        logger.debug("[Extraction] Создание менеджера файлов")
        return ExtractionFileManager()
    
    @staticmethod
    def create_extraction_pipeline(
        ocr_provider: Optional[IOCRProvider] = None,
        image_preprocessor: Optional[IImagePreprocessor] = None,
        file_manager: Optional[ExtractionFileManager] = None,
        output_dir: Optional[Path] = None
    ) -> IExtractionPipeline:
        """
        Создает пайплайн extraction для домена Extraction.
        
        Args:
            ocr_provider: Провайдер OCR (опционально)
            image_preprocessor: Препроцессор изображений (опционально)
            file_manager: Менеджер файлов (опционально)
            output_dir: Директория для сохранения raw_ocr результатов
            
        Returns:
            Пайплайн extraction, реализующий интерфейс IExtractionPipeline
        """
        logger.debug("[Extraction] Создание пайплайна extraction")
        
        # Создаем компоненты если они не предоставлены
        if ocr_provider is None:
            ocr_provider = ExtractionComponentFactory.create_ocr_provider()
        
        if image_preprocessor is None:
            image_preprocessor = ExtractionComponentFactory.create_image_preprocessor()
        
        if file_manager is None:
            file_manager = ExtractionComponentFactory.create_file_manager()
        
        # Определяем output_dir если не указан
        if output_dir is None:
            from config.settings import OUTPUT_DIR
            output_dir = OUTPUT_DIR / "raw_ocr"
        
        return ExtractionPipeline(
            ocr_provider=ocr_provider,
            image_preprocessor=image_preprocessor,
            file_manager=file_manager,
            output_dir=output_dir
        )
    
    @staticmethod
    def create_default_extraction_pipeline() -> IExtractionPipeline:
        """
        Создает пайплайн extraction с настройками по умолчанию.
        
        Returns:
            Полностью сконфигурированный пайплайн extraction
        """
        logger.info("[Extraction] Создание пайплайна extraction с настройками по умолчанию")
        
        # Создаем все компоненты с настройками по умолчанию
        ocr_provider = ExtractionComponentFactory.create_ocr_provider()
        image_preprocessor = ExtractionComponentFactory.create_image_preprocessor()
        file_manager = ExtractionComponentFactory.create_file_manager()
        
        # Определяем output_dir
        from config.settings import OUTPUT_DIR
        output_dir = OUTPUT_DIR / "raw_ocr"
        
        # Создаем пайплайн
        return ExtractionPipeline(
            ocr_provider=ocr_provider,
            image_preprocessor=image_preprocessor,
            file_manager=file_manager,
            output_dir=output_dir
        )
    
    @staticmethod
    def get_extraction_info() -> Dict[str, Any]:
        """
        Возвращает информацию о домене Extraction.
        
        Returns:
            Словарь с информацией о доступных компонентах и их возможностях
        """
        logger.debug("[Extraction] Получение информации о домене Extraction")
        
        return {
            "domain": "Extraction",
            "responsibility": "Preprocessing изображений + OCR распознавание",
            "output": "raw_ocr.json",
            "components": {
                "ocr_provider": "GoogleVisionOCRAdapter",
                "image_preprocessor": "ImagePreprocessorAdapter",
                "file_manager": "ExtractionFileManager",
                "extraction_pipeline": "ExtractionPipeline"
            },
            "capabilities": [
                "image_preprocessing",
                "ocr_recognition",
                "raw_ocr_generation",
                "file_management"
            ],
            "dependencies": ["Google Cloud Vision API", "OpenCV", "Pillow"]
        }
