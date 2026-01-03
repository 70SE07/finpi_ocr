"""
Исключения для домена Extraction.

Специфичные для обработки изображений и OCR ошибки.
"""

from typing import Optional


class ExtractionError(Exception):
    """Базовое исключение для ошибок домена Extraction."""
    
    def __init__(
        self, 
        message: str, 
        component: Optional[str] = None, 
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.component = component
        self.original_error = original_error
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        msg = f"Extraction Error: {self.message}"
        if self.component:
            msg += f" (Component: {self.component})"
        if self.original_error:
            msg += f" [Original: {type(self.original_error).__name__}: {str(self.original_error)}]"
        return msg


class ImageProcessingError(ExtractionError):
    """Ошибка обработки изображения."""
    pass


class ImageNotFoundError(ImageProcessingError):
    """Изображение не найдено."""
    pass


class ImageDecodingError(ImageProcessingError):
    """Ошибка декодирования изображения."""
    pass


class OCRProcessingError(ExtractionError):
    """Ошибка обработки OCR."""
    pass


class OCRProviderError(OCRProcessingError):
    """Ошибка провайдера OCR."""
    pass


class OCRResponseError(OCRProcessingError):
    """Ошибка в ответе OCR."""
    pass


class ExtractionConfigurationError(ExtractionError):
    """Ошибка конфигурации домена Extraction."""
    pass


class ExtractionFileSystemError(ExtractionError):
    """Ошибка файловой системы в домене Extraction."""
    pass


class ExtractionFileNotFoundError(ExtractionFileSystemError):
    """Файл не найден в домене Extraction."""
    pass


class ExtractionFileWriteError(ExtractionFileSystemError):
    """Ошибка записи файла в домене Extraction."""
    pass


class ExtractionValidationError(ExtractionError):
    """Ошибка валидации данных в домене Extraction."""
    pass
