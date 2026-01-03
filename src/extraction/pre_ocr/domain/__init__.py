"""Pre-OCR Domain exports."""

from .interfaces import (
    IImagePreprocessor,
    IPreprocessingStage,
    IImageCompressionStage,
    IImagePreparationStage,
    IAnalyzerStage,
    ISelectorStage,
    IExecutorStage,
    IEncoderStage,
)
from .exceptions import (
    PreOCRError,
    CompressionError,
    PreparationError,
    AnalysisError,
    SelectionError,
    ExecutionError,
    EncodingError,
)

__all__ = [
    'IImagePreprocessor',
    'IPreprocessingStage',
    'IImageCompressionStage',
    'IImagePreparationStage',
    'IAnalyzerStage',
    'ISelectorStage',
    'IExecutorStage',
    'IEncoderStage',
    'PreOCRError',
    'CompressionError',
    'PreparationError',
    'AnalysisError',
    'SelectionError',
    'ExecutionError',
    'EncodingError',
]
