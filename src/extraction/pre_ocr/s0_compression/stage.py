"""
Stage 0: Compression (Сжатие).

Адаптивное сжатие изображения на основе геометрии и плотности.

КОНТРАКТЫ:
  Входные: CompressionRequest (с валидацией размеров и file_size)
  Выходные: CompressionResponse (с гарантиями positive значений)

Входные данные:
- image: np.ndarray (BGR, нормализованный размер из Stage 1)
- original_bytes: размер исходного файла в байтах

Выходные данные:
- CompressionResult с:
  - image: np.ndarray (сжатое изображение)
  - scale_factor: float (масштаб сжатия)
  - quality: int (рекомендуемое качество JPEG)
  - metadata: dict с информацией о сжатии
"""

import numpy as np
import cv2
from dataclasses import dataclass
from loguru import logger
from pydantic import ValidationError

from ..domain.interfaces import IImageCompressionStage
from src.domain.contracts import CompressionRequest, CompressionResponse, ContractValidationError
from config.settings import (
    MAX_IMAGE_SIZE, JPEG_QUALITY,
    ADAPTIVE_HEIGHT_RATIO, ADAPTIVE_DENSITY_THRESHOLD,
    ADAPTIVE_LONG_RECEIPT_SIZE, ADAPTIVE_HIGH_DENSITY_SIZE
)


@dataclass
class CompressionResult:
    """Результат сжатия изображения."""
    image: np.ndarray
    original_size: tuple[int, int]  # (width, height)
    compressed_size: tuple[int, int]  # (width, height)
    scale_factor: float
    quality: int
    method: str  # "adaptive", "fixed", "none"
    was_compressed: bool
    metadata: dict  # Для экспорта в pipeline


class ImageCompressionStage(IImageCompressionStage):
    """
    Stage 0: Compression.
    
    Сжимает изображение адаптивно на основе его геометрии и плотности.
    """
    
    def __init__(self, mode: str = "adaptive"):
        """
        Args:
            mode: "adaptive" (рекомендуется), "fixed", "none"
        """
        self.mode = mode
        logger.debug(f"[Stage 0: Compression] Инициализирован (mode={mode})")
    
    def compute_target_size(self, width: int, height: int, file_size_bytes: int) -> tuple[int, int]:
        """
        Вычисляет целевой размер для сжатия БЕЗ загрузки полного изображения.
        
        Позволяет pipeline прочитать размер файла и загрузить изображение сразу
        в целевом размере, экономя 60% памяти.
        
        ОПТИМИЗАЦИЯ: Используется ДО загрузки изображения в pipeline
        
        ВАЛИДАЦИЯ: Входные параметры проверяются через CompressionRequest контракт
        
        Args:
            width: исходная ширина изображения
            height: исходная высота изображения
            file_size_bytes: размер файла в байтах
            
        Returns:
            (target_width, target_height) - целевой размер для cv2.resize
            
        Raises:
            ContractValidationError: если параметры невалидны
        """
        # ✅ ВАЛИДАЦИЯ входных параметров
        try:
            request = CompressionRequest(
                file_path="<buffer>",  # Мы работаем с памятью, не файлом
                original_width=width,
                original_height=height,
                file_size_bytes=file_size_bytes
            )
        except ValidationError as e:
            raise ContractValidationError("S0", "CompressionRequest", e.errors())
        
        density = request.file_size_bytes / (request.original_width * request.original_height) if request.original_width * request.original_height > 0 else 0
        
        logger.debug(f"[Stage 0] compute_target_size: {width}x{height}, density: {density:.3f} b/px")
        
        if self.mode == "none":
            return (width, height)
        elif self.mode == "fixed":
            return self._get_fixed_size(width, height)
        else:  # adaptive
            return self._get_adaptive_size(width, height, density)
    
    def compress(self, image: np.ndarray, original_bytes: int) -> CompressionResult:
        """
        Сжимает уже загруженное изображение.
        
        ПРИМЕЧАНИЕ: Рекомендуется вычислить target_size через compute_target_size()
        перед загрузкой и загрузить изображение сразу в целевом размере.
        
        ВОЗВРАЩАЕТ: Гарантированный валидный CompressionResponse
        
        Args:
            image: np.ndarray (BGR или Grayscale)
            original_bytes: размер исходного файла в байтах
            
        Returns:
            CompressionResult с валидированными значениями
            
        Raises:
            ContractValidationError: если расчёты привели к невалидным значениям
        """
        h, w = image.shape[:2]
        original_size = (w, h)
        density = original_bytes / (w * h) if w * h > 0 else 0
        
        logger.debug(f"[Stage 0] Входной размер: {w}x{h}, плотность: {density:.3f} b/px")
        
        # Определяем целевой размер
        if self.mode == "none":
            target_size = original_size
            method = "none"
            scale_factor = 1.0
        elif self.mode == "fixed":
            target_size = self._get_fixed_size(w, h)
            method = "fixed"
            scale_factor = min(target_size[0] / w, target_size[1] / h)
        else:  # adaptive
            target_size = self._get_adaptive_size(w, h, density)
            method = "adaptive"
            scale_factor = min(target_size[0] / w, target_size[1] / h)
        
        # Если сжатие не требуется
        if scale_factor >= 1.0:
            logger.debug(f"[Stage 0] Изображение уже в целевом размере")
            
            # ✅ ВАЛИДАЦИЯ выходного контракта
            try:
                response = CompressionResponse(
                    target_width=original_size[0],
                    target_height=original_size[1],
                    jpeg_quality=JPEG_QUALITY,
                    adaptive_density=density,
                    scale_factor=1.0
                )
            except ValidationError as e:
                raise ContractValidationError("S0", "CompressionResponse", e.errors())
            
            return CompressionResult(
                image=image,
                original_size=original_size,
                compressed_size=original_size,
                scale_factor=1.0,
                quality=response.jpeg_quality,
                method="none",
                was_compressed=False,
                metadata={
                    "original_size": original_size,
                    "compressed_size": original_size,
                    "scale_factor": 1.0,
                    "quality": response.jpeg_quality,
                    "method": "none",
                    "response_contract": response.model_dump()
                }
            )
        
        # Ресайзим
        compressed = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
        logger.debug(f"[Stage 0] {method} сжатие: {w}x{h} → {target_size[0]}x{target_size[1]} (x{scale_factor:.2f})")
        
        # ✅ ВАЛИДАЦИЯ выходного контракта
        try:
            response = CompressionResponse(
                target_width=target_size[0],
                target_height=target_size[1],
                jpeg_quality=JPEG_QUALITY,
                adaptive_density=density,
                scale_factor=scale_factor
            )
        except ValidationError as e:
            raise ContractValidationError("S0", "CompressionResponse", e.errors())
        
        return CompressionResult(
            image=compressed,
            original_size=original_size,
            compressed_size=target_size,
            scale_factor=scale_factor,
            quality=response.jpeg_quality,
            method=method,
            was_compressed=True,
            metadata={
                "original_size": original_size,
                "compressed_size": target_size,
                "scale_factor": scale_factor,
                "quality": response.jpeg_quality,
                "method": method,
                "response_contract": response.model_dump()
            }
        )
    
    def _get_adaptive_size(self, w: int, h: int, density: float) -> tuple[int, int]:
        """Адаптивный размер на основе геометрии и плотности."""
        long_receipt = h / w > ADAPTIVE_HEIGHT_RATIO if w > 0 else False
        high_density = density > ADAPTIVE_DENSITY_THRESHOLD
        
        if long_receipt:
            target = ADAPTIVE_LONG_RECEIPT_SIZE
            logger.debug(f"[Stage 0] Длинный чек (H/W={h/w:.2f}) → {target}px")
        elif high_density:
            target = ADAPTIVE_HIGH_DENSITY_SIZE
            logger.debug(f"[Stage 0] Высокая плотность ({density:.3f} b/px) → {target}px")
        else:
            target = MAX_IMAGE_SIZE
            logger.debug(f"[Stage 0] Стандартный размер → {target}px")
        
        return self._get_fixed_size_by_target(w, h, target)
    
    def _get_fixed_size(self, w: int, h: int) -> tuple[int, int]:
        """Фиксированный размер с сохранением aspect ratio."""
        if max(w, h) <= MAX_IMAGE_SIZE:
            return (w, h)
        
        aspect = w / h if h > 0 else 1.0
        
        if w > h:
            new_w = MAX_IMAGE_SIZE
            new_h = int(MAX_IMAGE_SIZE / aspect)
        else:
            new_h = MAX_IMAGE_SIZE
            new_w = int(MAX_IMAGE_SIZE * aspect)
        
        return (new_w, new_h)
    
    def _get_fixed_size_by_target(self, w: int, h: int, target: int) -> tuple[int, int]:
        """Размер с заданным максимумом."""
        if max(w, h) <= target:
            return (w, h)
        
        aspect = w / h if h > 0 else 1.0
        
        if w > h:
            new_w = target
            new_h = int(target / aspect)
        else:
            new_h = target
            new_w = int(target * aspect)
        
        return (new_w, new_h)
