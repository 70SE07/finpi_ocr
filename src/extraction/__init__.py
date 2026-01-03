"""
Домен Extraction: Pre-OCR + OCR обработка.

Этот домен отвечает за:
1. Pre-OCR обработку изображений (deskew, rotation, enhancement)
2. Выполнение OCR через Google Vision API
3. Сохранение сырых результатов в формате RawOCRResult

Граница домена: contracts.RawOCRResult
"""

# Экспортируем основные классы
from .pre_ocr import AdaptivePreOCRPipeline
from .infrastructure.ocr.google_vision_ocr import GoogleVisionOCR

# Экспортируем application слой
from .application.factory import ExtractionComponentFactory
from .application.extraction_pipeline import ExtractionPipeline

__all__ = [
    'AdaptivePreOCRPipeline',
    'GoogleVisionOCR',
    'ExtractionComponentFactory',
    'ExtractionPipeline',
]
