"""
Domain слой домена Extraction.

Содержит интерфейсы (абстрактные классы) и исключения для Extraction домена.
"""

from .interfaces import (
    IOCRProvider,
    IImagePreprocessor,
    IExtractionPipeline,
)

from .exceptions import (
    ExtractionError,
    ImageProcessingError,
    ImageNotFoundError,
    ImageDecodingError,
    OCRProcessingError,
    OCRProviderError,
    OCRResponseError,
    ExtractionConfigurationError,
    ExtractionFileSystemError,
    ExtractionFileNotFoundError,
    ExtractionFileWriteError,
    ExtractionValidationError,
)

__all__ = [
    # Интерфейсы
    "IOCRProvider",
    "IImagePreprocessor",
    "IExtractionPipeline",
    
    # Исключения
    "ExtractionError",
    "ImageProcessingError",
    "ImageNotFoundError",
    "ImageDecodingError",
    "OCRProcessingError",
    "OCRProviderError",
    "OCRResponseError",
    "ExtractionConfigurationError",
    "ExtractionFileSystemError",
    "ExtractionFileNotFoundError",
    "ExtractionFileWriteError",
    "ExtractionValidationError",
]

