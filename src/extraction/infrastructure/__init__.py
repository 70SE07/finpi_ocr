"""
Инфраструктурный слой домена Extraction.

Содержит реализации инфраструктурных компонентов.
"""

from .ocr.google_vision_ocr import GoogleVisionOCR
from .file_manager import ExtractionFileManager

__all__ = [
    # OCR
    "GoogleVisionOCR",
    
    # Менеджеры
    "ExtractionFileManager",
]
