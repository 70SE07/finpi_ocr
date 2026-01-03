"""
Stage 5: Encoder (Кодировщик).

Кодирует обработанное изображение в JPEG bytes для отправки в Google Vision API.

КОНТРАКТЫ:
  Входные: EncoderRequest (валидированный quality [50-95])
  Выходные: EncoderResponse (валидированный size, quality, ratio)

Входные данные:
- image: np.ndarray (ЧБ, обработанное, после Stage 4)
- quality: int (рекомендуемое качество, от Stage 0)
- image_size: tuple (ширина, высота) для адаптивного качества

Выходные данные:
- bytes (JPEG кодированное изображение)
"""

import cv2
import numpy as np
import math
from pydantic import ValidationError
from loguru import logger

from config.settings import JPEG_QUALITY
from src.domain.contracts import (
    EncoderRequest, EncoderResponse,
    ContractValidationError
)


class ImageEncoderStage:
    """
    Stage 5: Encoder (Кодировщик).

    Кодирует обработанное изображение в JPEG bytes для отправки в Google Vision API.
    
    КОНТРАКТЫ:
      Входные: EncoderRequest (quality [50-95])
      Выходные: EncoderResponse (validated sizes, quality, ratio)
    """
    
    def __init__(self):
        logger.debug("[Stage 5: Encoder] Инициализирован (с контрактами)")

    def encode(
        self, 
        image: np.ndarray, 
        quality: int = None, 
        image_size: tuple = None
    ) -> bytes:
        """
        Кодирует изображение в JPEG bytes.
        
        ВОЗВРАЩАЕТ: Гарантированный валидный JPEG (EncoderResponse валидирован)
        
        Args:
            image: np.ndarray (ЧБ или BGR)
            quality: int (0-100), если None используется из config
            image_size: tuple (w, h) для адаптивного качества
            
        Returns:
            bytes (JPEG)
            
        Raises:
            ContractValidationError: если качество невалидно или кодирование не удалось
        """
        if quality is None:
            quality = JPEG_QUALITY
        
        # Получаем размеры изображения
        h, w = image.shape[:2]
        
        # ✅ ВАЛИДАЦИЯ входного контракта
        try:
            encoder_request = EncoderRequest(
                image_data=image.tobytes(),
                width=w,
                height=h,
                quality=quality
            )
        except ValidationError as e:
            raise ContractValidationError("S5", "EncoderRequest", e.errors())
        
        # Адаптивное качество на основе размера изображения
        if image_size:
            orig_w, orig_h = image_size
            pixels = orig_w * orig_h
            
            # Если изображение очень маленькое, можно снизить качество
            if pixels < 500000:  # < 500K пикселей
                quality = min(quality, 75)
                logger.debug(f"[Stage 5] Малое изображение ({pixels} px) → качество {quality}%")
            # Если очень большое, повысить качество
            elif pixels > 3000000:  # > 3M пикселей
                quality = min(quality, 85)
                logger.debug(f"[Stage 5] Большое изображение ({pixels} px) → качество {quality}%")
        
        # Кодирование в JPEG
        original_size_bytes = w * h
        
        success, encoded_img = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        
        # ✅ ПРОВЕРКА: успешно ли кодирование
        if not success or encoded_img is None:
            logger.error("[Stage 5] Ошибка кодирования JPEG")
            raise ValueError("Failed to encode image to JPEG")
        
        image_bytes = encoded_img.tobytes()
        encoded_size_bytes = len(image_bytes)
        
        # ✅ ВАЛИДАЦИЯ выходного контракта
        try:
            encoder_response = EncoderResponse(
                jpeg_bytes=image_bytes,
                jpeg_quality=quality,
                original_size_kb=original_size_bytes / 1024.0,
                encoded_size_kb=encoded_size_bytes / 1024.0,
                compression_ratio=original_size_bytes / max(encoded_size_bytes, 1)  # Avoid div by 0
            )
        except ValidationError as e:
            raise ContractValidationError("S5", "EncoderResponse", e.errors())
        
        logger.debug(
            f"[Stage 5] ✅ Закодировано в JPEG: {encoded_size_bytes} bytes, "
            f"качество {quality}%, ratio {encoder_response.compression_ratio:.2f}x"
        )
        
        return image_bytes

