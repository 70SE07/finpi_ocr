"""
Адаптеры домена Extraction.

Содержит адаптеры для существующих компонентов, реализующие интерфейсы.
"""

from .google_vision_adapter import GoogleVisionOCRAdapter
from .image_preprocessor_adapter import ImagePreprocessorAdapter

__all__ = [
    "GoogleVisionOCRAdapter",
    "ImagePreprocessorAdapter",
]

