"""
Исключения для домена Parsing.

Специфичные для парсинга чеков ошибки.
"""


class ParsingError(Exception):
    """Базовое исключение для ошибок домена Parsing."""
    
    def __init__(self, message: str, component: str = None, original_error: Exception = None):
        self.message = message
        self.component = component
        self.original_error = original_error
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        msg = f"Parsing Error: {self.message}"
        if self.component:
            msg += f" (Component: {self.component})"
        if self.original_error:
            msg += f" [Original: {type(self.original_error).__name__}: {str(self.original_error)}]"
        return msg


class LayoutProcessingError(ParsingError):
    """Ошибка обработки layout."""
    pass


class LocaleDetectionError(ParsingError):
    """Ошибка определения локали."""
    pass


class MetadataExtractionError(ParsingError):
    """Ошибка извлечения метаданных."""
    pass


class SemanticExtractionError(ParsingError):
    """Ошибка семантического извлечения."""
    pass


class ParsingConfigurationError(ParsingError):
    """Ошибка конфигурации домена Parsing."""
    pass


class ParsingFileSystemError(ParsingError):
    """Ошибка файловой системы в домене Parsing."""
    pass


class ParsingFileNotFoundError(ParsingFileSystemError):
    """Файл не найден в домене Parsing."""
    pass


class ParsingFileWriteError(ParsingFileSystemError):
    """Ошибка записи файла в домене Parsing."""
    pass


class ParsingValidationError(ParsingError):
    """Ошибка валидации данных в домене Parsing."""
    pass


class ParsingDataFormatError(ParsingError):
    """Ошибка формата данных (некорректный raw_ocr формат)."""
    pass
