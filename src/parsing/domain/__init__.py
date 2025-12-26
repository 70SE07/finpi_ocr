"""
Domain слой домена Parsing.

Содержит интерфейсы (абстрактные классы) и исключения для Parsing домена.
"""

from .interfaces import (
    IReceiptParser,
    ILayoutProcessor,
    ILocaleDetector,
    IMetadataExtractor,
    ISemanticExtractor,
    IParsingPipeline,
)

from .exceptions import (
    ParsingError,
    LayoutProcessingError,
    LocaleDetectionError,
    MetadataExtractionError,
    SemanticExtractionError,
    ParsingConfigurationError,
    ParsingFileSystemError,
    ParsingFileNotFoundError,
    ParsingFileWriteError,
    ParsingValidationError,
    ParsingDataFormatError,
)

__all__ = [
    # Интерфейсы
    "IReceiptParser",
    "ILayoutProcessor",
    "ILocaleDetector",
    "IMetadataExtractor",
    "ISemanticExtractor",
    "IParsingPipeline",
    
    # Исключения
    "ParsingError",
    "LayoutProcessingError",
    "LocaleDetectionError",
    "MetadataExtractionError",
    "SemanticExtractionError",
    "ParsingConfigurationError",
    "ParsingFileSystemError",
    "ParsingFileNotFoundError",
    "ParsingFileWriteError",
    "ParsingValidationError",
    "ParsingDataFormatError",
]

