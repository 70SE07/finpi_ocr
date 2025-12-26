"""
Адаптер для GoogleVisionOCR, реализующий интерфейс IOCRProvider (домен Extraction).

Позволяет использовать существующий GoogleVisionOCR через единый интерфейс домена Extraction.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from ...domain.interfaces import IOCRProvider
from ...domain.exceptions import OCRProviderError, OCRResponseError
from ...ocr.google_vision_ocr import GoogleVisionOCR as OriginalGoogleVisionOCR
from contracts.raw_ocr_schema import RawOCRResult


class GoogleVisionOCRAdapter(IOCRProvider):
    """
    Адаптер для GoogleVisionOCR (домен Extraction).
    
    Реализует интерфейс IOCRProvider, делегируя вызовы оригинальному GoogleVisionOCR.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Инициализация адаптера.
        
        Args:
            credentials_path: Путь к credentials файлу Google Cloud
        """
        try:
            self._original_ocr = OriginalGoogleVisionOCR(credentials_path)
            logger.debug("[Extraction] GoogleVisionOCRAdapter инициализирован")
        except Exception as e:
            raise OCRProviderError(
                message="Не удалось инициализировать GoogleVisionOCR",
                component="GoogleVisionOCRAdapter",
                original_error=e
            )
    
    def recognize(self, image_content: bytes) -> Dict[str, Any]:
        """
        Распознает текст на изображении.
        
        Args:
            image_content: Байты изображения
            
        Returns:
            Словарь с результатами OCR в формате raw_ocr
            
        Raises:
            OCRResponseError: Если произошла ошибка при распознавании
        """
        try:
            logger.debug("[Extraction] Вызов GoogleVisionOCR.recognize()")
            result = self._original_ocr.recognize(image_content)
            
            # Конвертируем RawOCRResult в словарь
            if isinstance(result, RawOCRResult):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                raise OCRResponseError(
                    message=f"Неожиданный тип результата: {type(result)}",
                    component="GoogleVisionOCRAdapter"
                )
                
        except Exception as e:
            raise OCRResponseError(
                message="Ошибка при распознавании текста",
                component="GoogleVisionOCRAdapter",
                original_error=e
            )
    
    def recognize_from_file(self, image_path: Path) -> Dict[str, Any]:
        """
        Распознает текст из файла изображения.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Словарь с результатами OCR в формате raw_ocr
            
        Raises:
            OCRResponseError: Если произошла ошибка при распознавании
        """
        try:
            logger.debug(f"[Extraction] Вызов GoogleVisionOCR.recognize_from_file() для {image_path}")
            result = self._original_ocr.recognize_from_file(image_path)
            
            # Конвертируем RawOCRResult в словарь
            if isinstance(result, RawOCRResult):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                raise OCRResponseError(
                    message=f"Неожиданный тип результата: {type(result)}",
                    component="GoogleVisionOCRAdapter"
                )
                
        except Exception as e:
            raise OCRResponseError(
                message=f"Ошибка при распознавании файла: {image_path}",
                component="GoogleVisionOCRAdapter",
                original_error=e
            )
