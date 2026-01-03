"""
Pre-OCR Domain: Исключения.
"""


class PreOCRError(Exception):
    """Базовое исключение для Pre-OCR."""
    pass


class CompressionError(PreOCRError):
    """Ошибка при сжатии изображения."""
    pass


class PreparationError(PreOCRError):
    """Ошибка при подготовке изображения."""
    pass


class AnalysisError(PreOCRError):
    """Ошибка при анализе метрик."""
    pass


class SelectionError(PreOCRError):
    """Ошибка при выборе стратегии."""
    pass


class ExecutionError(PreOCRError):
    """Ошибка при применении фильтров."""
    pass


class EncodingError(PreOCRError):
    """Ошибка при кодировании изображения."""
    pass
