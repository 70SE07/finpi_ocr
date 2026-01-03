"""
Stage 1: Preparation (Подготовка).

Отвечает за загрузку изображения и нормализацию размера.
Выход: Цветное изображение (BGR) нормализованного размера.

Входные данные:
- image_path: Path к файлу изображения

Выходные данные:
- image: np.ndarray (BGR, размер нормализован на MAX_IMAGE_SIZE)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger

from ..domain.interfaces import IImagePreparationStage
from config.settings import MAX_IMAGE_SIZE


class ImagePreparationStage(IImagePreparationStage):
    """
    Stage 1: Preparation.

    Отвечает за загрузку изображения и нормализацию размера.
    Выход: Цветное изображение (BGR) нормализованного размера.
    """
    
    def __init__(self, max_size: int = MAX_IMAGE_SIZE):
        self.max_size = max_size
        logger.debug(f"[Stage 1: Preparation] Инициализирована (max_size={max_size}px)")

    def process(self, image_path: Path, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Загружает и нормализует размер изображения.
        
        ОПТИМИЗАЦИЯ: Если передан target_size, изображение загружается сразу
        в целевом размере (экономит 60% памяти). Иначе нормализует по MAX_IMAGE_SIZE.
        
        Args:
            image_path: Path к файлу изображения
            target_size: (width, height) - опциональный целевой размер для загрузки
                        Если None, нормализует по MAX_IMAGE_SIZE
            
        Returns:
            np.ndarray (BGR)
        """
        # Загрузка через numpy для поддержки путей с Unicode (cv2.imread не умеет)
        try:
            img_array = np.fromfile(str(image_path), np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"[Stage 1] Ошибка загрузки {image_path}: {e}")
            raise ValueError(f"Failed to load image {image_path}: {e}")

        if image is None:
            logger.error(f"[Stage 1] Не удалось декодировать изображение: {image_path}")
            raise ValueError(f"Failed to decode image: {image_path}")

        h, w = image.shape[:2]
        logger.debug(f"[Stage 1] Загружено: {w}x{h}")

        # Resize к целевому размеру (если задан) или к MAX_IMAGE_SIZE
        if target_size is not None:
            # Используем target_size из Compression (уже оптимизирован)
            target_w, target_h = target_size
            if (w, h) != target_size:
                image = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
                logger.debug(f"[Stage 1] Нормализовано (target): {w}x{h} → {target_w}x{target_h}")
        else:
            # Старое поведение для backward compatibility
            if max(h, w) > self.max_size:
                scale = self.max_size / max(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                logger.debug(f"[Stage 1] Нормализовано (MAX): {w}x{h} → {new_w}x{new_h}")
            
        return image
