"""
Инфраструктурный слой домена Extraction.

Содержит реализации инфраструктурных компонентов.
"""

from .ocr.google_vision_ocr import GoogleVisionOCR

__all__ = [
    # OCR
    "GoogleVisionOCR",
]
