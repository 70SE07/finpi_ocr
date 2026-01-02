"""
Фабрика для создания компонентов домена Extraction.

Предоставляет удобные методы для создания и конфигурации
всех компонентов домена Extraction через единый интерфейс.

ВАЖНО: ExtractionPipeline возвращает RawOCRResult (контракт D1->D2).
"""

from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from ..domain.interfaces import IOCRProvider, IImagePreprocessor, IExtractionPipeline
from ..infrastructure.ocr.google_vision_ocr import GoogleVisionOCR
from ..pre_ocr.pipeline import PreOCRPipeline
from .extraction_pipeline import ExtractionPipeline


class ExtractionComponentFactory:
    """
    Фабрика для создания компонентов домена Extraction.
    
    Домен Extraction отвечает за:
    - Preprocessing изображений
    - OCR распознавание текста
    - Возврат RawOCRResult (контракт D1->D2)
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
        return GoogleVisionOCR(credentials_path)
    
    @staticmethod
    def create_image_preprocessor() -> IImagePreprocessor:
        """
        Создает препроцессор изображений для домена Extraction.
        
        Returns:
            Препроцессор изображений, реализующий интерфейс IImagePreprocessor
        """
        logger.debug("[Extraction] Создание препроцессора изображений")
        return PreOCRPipeline()
    
    @staticmethod
    def create_extraction_pipeline(
        ocr_provider: Optional[IOCRProvider] = None,
        image_preprocessor: Optional[IImagePreprocessor] = None,
    ) -> ExtractionPipeline:
        """
        Создает пайплайн extraction для домена Extraction.
        
        Args:
            ocr_provider: Провайдер OCR (опционально)
            image_preprocessor: Препроцессор изображений (опционально)
            
        Returns:
            ExtractionPipeline, возвращающий RawOCRResult
        """
        logger.debug("[Extraction] Создание пайплайна extraction")
        
        # Создаем компоненты если они не предоставлены
        if ocr_provider is None:
            ocr_provider = ExtractionComponentFactory.create_ocr_provider()
        
        if image_preprocessor is None:
            image_preprocessor = ExtractionComponentFactory.create_image_preprocessor()
        
        return ExtractionPipeline(
            ocr_provider=ocr_provider,
            image_preprocessor=image_preprocessor,
        )
    
    @staticmethod
    def create_default_extraction_pipeline() -> ExtractionPipeline:
        """
        Создает пайплайн extraction с настройками по умолчанию.
        
        Returns:
            ExtractionPipeline, готовый к использованию
            
        Пример использования:
            pipeline = ExtractionComponentFactory.create_default_extraction_pipeline()
            raw_ocr = pipeline.process_image(Path("receipt.jpg"))
            # raw_ocr — это RawOCRResult (контракт D1->D2)
        """
        logger.info("[Extraction] Создание пайплайна extraction с настройками по умолчанию")
        
        ocr_provider = ExtractionComponentFactory.create_ocr_provider()
        image_preprocessor = ExtractionComponentFactory.create_image_preprocessor()
        
        return ExtractionPipeline(
            ocr_provider=ocr_provider,
            image_preprocessor=image_preprocessor,
        )
    
    @staticmethod
    def get_extraction_info() -> Dict[str, Any]:
        """
        Возвращает информацию о домене Extraction.
        
        Returns:
            Словарь с информацией о доступных компонентах
        """
        return {
            "domain": "Extraction",
            "responsibility": "Preprocessing изображений + OCR распознавание",
            "output": "RawOCRResult (контракт D1->D2)",
            "components": {
                "ocr_provider": "GoogleVisionOCR",
                "image_preprocessor": "PreOCRPipeline",
                "extraction_pipeline": "ExtractionPipeline"
            },
            "capabilities": [
                "image_preprocessing",
                "ocr_recognition",
                "words[] с координатами (ADR-006)"
            ],
            "dependencies": ["Google Cloud Vision API", "OpenCV", "Pillow"]
        }
