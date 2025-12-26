"""
Адаптеры домена Parsing.

Содержат адаптеры для существующих компонентов, реализующие интерфейсы.
"""

from .layout_processor_adapter import LayoutProcessorAdapter
from .locale_detector_adapter import LocaleDetectorAdapter
from .metadata_extractor_adapter import MetadataExtractorAdapter
from .semantic_extractor_adapter import SemanticExtractorAdapter

__all__ = [
    "LayoutProcessorAdapter",
    "LocaleDetectorAdapter",
    "MetadataExtractorAdapter",
    "SemanticExtractorAdapter",
]

