"""
Image File Reader для pre-OCR пайплайна.

Чтение и декодирование изображений из файлов.
Операция отвечает только за чтение файла и декодирование в numpy array.
"""

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from loguru import logger


class ImageFileReader:
    """
    Читает изображение из файла и декодирует в numpy array.
    
    ЦКП: декодированное изображение (numpy.ndarray) и исходные байты.
    """
    
    @staticmethod
    def read(image_path: Path) -> Tuple[np.ndarray, bytes]:
        """
        Читает файл изображения и декодирует в numpy array.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Кортеж: (decoded_image, raw_bytes)
            - decoded_image: numpy.ndarray (BGR формат)
            - raw_bytes: исходные байты файла
            
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если не удалось декодировать изображение
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Читаем файл
        with open(image_path, "rb") as f:
            raw_bytes = f.read()
        
        # Декодируем изображение
        nparr = np.frombuffer(raw_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError(f"Failed to decode image: {image_path}")
        
        logger.debug(f"[ImageFileReader] Изображение прочитано: {image_path.name}, размер: {image.shape}")
        
        return image, raw_bytes
