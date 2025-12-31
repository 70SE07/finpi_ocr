"""
Адаптер для GoogleVisionOCR, реализующий интерфейс IOCRProvider (домен Extraction).

Позволяет использовать существующий GoogleVisionOCR через единый интерфейс домена Extraction.

ВАЖНО: Возвращает RawOCRResult из contracts/d1_extraction_dto.py
"""

from pathlib import Path
from typing import Optional
from loguru import logger

from ...domain.interfaces import IOCRProvider
from ...domain.exceptions import OCRProviderError, OCRResponseError
from ...ocr.google_vision_ocr import GoogleVisionOCR as OriginalGoogleVisionOCR
from contracts.d1_extraction_dto import RawOCRResult


class GoogleVisionOCRAdapter(IOCRProvider):
    """
    Адаптер для GoogleVisionOCR (домен Extraction).
    
    Реализует интерфейс IOCRProvider, делегируя вызовы оригинальному GoogleVisionOCR.
    Возвращает RawOCRResult — контракт D1->D2.
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
    
    def recognize(self, image_content: bytes, source_file: str = "unknown") -> RawOCRResult:
        """
        Распознает текст на изображении.
        
        Args:
            image_content: Байты изображения
            source_file: Имя исходного файла (для метаданных)
            
        Returns:
            RawOCRResult: Контракт D1->D2 с full_text и words[]
            
        Raises:
            OCRResponseError: Если произошла ошибка при распознавании
        """
        try:
            logger.debug("[Extraction] Вызов GoogleVisionOCR.recognize()")
            return self._original_ocr.recognize(image_content, source_file)
                
        except Exception as e:
            raise OCRResponseError(
                message="Ошибка при распознавании текста",
                component="GoogleVisionOCRAdapter",
                original_error=e
            )
    
    def recognize_from_file(self, image_path: Path) -> RawOCRResult:
        """
        Распознает текст из файла изображения.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            RawOCRResult: Контракт D1->D2
            
        Raises:
            OCRResponseError: Если произошла ошибка при распознавании
        """
        try:
            logger.debug(f"[Extraction] Вызов GoogleVisionOCR.recognize_from_file() для {image_path}")
            return self._original_ocr.recognize_from_file(image_path)
                
        except Exception as e:
            raise OCRResponseError(
                message=f"Ошибка при распознавании файла: {image_path}",
                component="GoogleVisionOCRAdapter",
                original_error=e
            )
