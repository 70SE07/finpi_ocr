"""
Application слой домена Extraction.

Содержит фабрики и оркестраторы для использования компонентов.
"""

from .factory import ExtractionComponentFactory
from .extraction_pipeline import ExtractionPipeline

__all__ = [
    "ExtractionComponentFactory",
    "ExtractionPipeline",
]

