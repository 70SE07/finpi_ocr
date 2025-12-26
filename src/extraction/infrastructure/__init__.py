"""
Инфраструктурный слой домена Extraction.

Содержит адаптеры для существующих компонентов.
"""

from .adapters.google_vision_adapter import GoogleVisionOCRAdapter
from .adapters.image_preprocessor_adapter import ImagePreprocessorAdapter
from .file_manager import ExtractionFileManager

__all__ = [
    # Адаптеры
    "GoogleVisionOCRAdapter",
    "ImagePreprocessorAdapter",
    
    # Менеджеры
    "ExtractionFileManager",
]
