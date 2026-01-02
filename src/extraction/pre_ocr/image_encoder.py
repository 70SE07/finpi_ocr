"""
Image Encoder для pre-OCR пайплайна.

Кодирование numpy array изображений в JPEG bytes.
Операция отвечает только за кодирование изображения в байты.
"""

import cv2
import numpy as np
from loguru import logger


class ImageEncoder:
    """
    Кодирует numpy array изображение в JPEG bytes.
    
    ЦКП: JPEG байты изображения.
    """
    
    @staticmethod
    def encode(image: np.ndarray, quality: int = 85) -> bytes:
        """
        Кодирует numpy array в JPEG bytes.
        
        Args:
            image: Изображение в формате numpy.ndarray (BGR или Grayscale)
            quality: Качество JPEG (0-100), по умолчанию 85
            
        Returns:
            JPEG байты изображения
            
        Raises:
            RuntimeError: Если не удалось закодировать изображение
        """
        success, buffer = cv2.imencode(
            ".jpg", 
            image, 
            [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        
        if not success:
            raise RuntimeError("Failed to encode processed image to JPEG")
        
        encoded_bytes = buffer.tobytes()
        
        logger.debug(
            f"[ImageEncoder] Изображение закодировано: "
            f"размер {len(encoded_bytes)} байт, качество {quality}"
        )
        
        return encoded_bytes
