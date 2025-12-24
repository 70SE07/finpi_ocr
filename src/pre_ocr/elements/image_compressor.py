"""
Image Compressor для pre-OCR пайплайна.

Сжатие изображения для оптимизации OCR:
- Уменьшение размера для ускорения обработки
- Сохранение качества для точности распознавания
- Адаптивные настройки по геометрии изображения

Используется в A/B тестах для определения оптимального места в пайплайне:
- Вариант A: Сжатие ДО поворота и кропа
- Вариант B: Сжатие ПОСЛЕ поворота и кропа
"""

import io
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from loguru import logger
from PIL import Image

from config.settings import (
    MAX_IMAGE_SIZE, JPEG_QUALITY,
    ADAPTIVE_HEIGHT_RATIO, ADAPTIVE_DENSITY_THRESHOLD
)


@dataclass
class CompressionResult:
    """Результат сжатия изображения."""

    image: np.ndarray
    original_size: tuple[int, int]  # (width, height)
    compressed_size: tuple[int, int]  # (width, height)
    original_bytes: int
    compressed_bytes: int
    scale_factor: float
    quality: int
    method: str  # "adaptive", "fixed", "none"
    was_compressed: bool


class ImageCompressor:
    """
    Сжатие изображения для OCR.

    Адаптивный алгоритм v2.1:
    - Длинные чеки (Height > 2.2 * Width) = 2400px (мелкие цены)
    - Высокая плотность (>0.55 b/px) = 1800px (консервативно)
    - Стандарт = 2200px (Lidl standard)
    """

    def __init__(
        self,
        max_dimension: int = MAX_IMAGE_SIZE,
        quality: int = JPEG_QUALITY,
        adaptive: bool = True,
    ):
        """
        Args:
            max_dimension: Максимальный размер стороны (по умолчанию 2200px)
            quality: Качество JPEG (0-100, по умолчанию 85)
            adaptive: Использовать адаптивные настройки по геометрии
        """
        self.max_dimension = max_dimension
        self.quality = quality
        self.adaptive = adaptive

    def _get_adaptive_settings(
        self,
        width: int,
        height: int,
        density: float,
    ) -> tuple[int, int]:
        """
        Вычисляет оптимальные настройки сжатия по геометрии и плотности.

        Hybrid v2.1:
        - Длинные чеки (Height > 2.2 * Width) = 2400px
        - Высокая плотность (>0.55 b/px) = 1800px
        - Стандарт = 2200px

        Returns:
            (max_dimension, quality)
        """
        # 1. Длинные чеки (Lidl style)
        if height > ADAPTIVE_HEIGHT_RATIO * width:
            return 2400, 85

        # 2. Высокая плотность = мелкий текст
        if density > ADAPTIVE_DENSITY_THRESHOLD:
            return 1800, 85

        # 3. Стандарт
        return MAX_IMAGE_SIZE, JPEG_QUALITY

    def compress(
        self,
        image: np.ndarray,
        original_bytes: int | None = None,
    ) -> CompressionResult:
        """
        Сжимает изображение для OCR.

        Args:
            image: BGR изображение (numpy array)
            original_bytes: Размер оригинала в байтах (для расчёта плотности)

        Returns:
            CompressionResult с сжатым изображением
        """
        h, w = image.shape[:2]
        original_size = (w, h)

        # Определяем настройки сжатия
        if self.adaptive and original_bytes:
            density = original_bytes / (w * h)
            max_dim, quality = self._get_adaptive_settings(w, h, density)
            method = "adaptive"
        else:
            max_dim = self.max_dimension
            quality = self.quality
            method = "fixed"

        # Вычисляем коэффициент масштабирования
        current_max = max(w, h)
        if current_max <= max_dim:
            # Изображение уже достаточно маленькое
            logger.info(f"[Compressor] Сжатие не требуется ({w}x{h} <= {max_dim}px)")

            # Просто кодируем в JPEG с заданным качеством
            _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            compressed_bytes = len(buffer)

            return CompressionResult(
                image=image,
                original_size=original_size,
                compressed_size=original_size,
                original_bytes=original_bytes or (w * h * 3),
                compressed_bytes=compressed_bytes,
                scale_factor=1.0,
                quality=quality,
                method=method,
                was_compressed=False,
            )

        # Масштабируем
        scale_factor = max_dim / current_max
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)

        # Используем INTER_AREA для уменьшения (лучше качество)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Кодируем в JPEG
        _, buffer = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
        compressed_bytes = len(buffer)

        logger.info(
            f"[Compressor] Сжато: {w}x{h} -> {new_w}x{new_h} "
            f"(scale={scale_factor:.2f}, quality={quality}, method={method})"
        )

        return CompressionResult(
            image=resized,
            original_size=original_size,
            compressed_size=(new_w, new_h),
            original_bytes=original_bytes or (w * h * 3),
            compressed_bytes=compressed_bytes,
            scale_factor=scale_factor,
            quality=quality,
            method=method,
            was_compressed=True,
        )

    def compress_bytes(
        self,
        image_bytes: bytes,
    ) -> tuple[bytes, CompressionResult]:
        """
        Сжимает изображение из байтов.

        Args:
            image_bytes: Исходное изображение в байтах

        Returns:
            (сжатые байты, CompressionResult)
        """
        # Декодируем
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Не удалось декодировать изображение")

        # Сжимаем
        result = self.compress(image, original_bytes=len(image_bytes))

        # Кодируем обратно в байты
        _, buffer = cv2.imencode(".jpg", result.image, [cv2.IMWRITE_JPEG_QUALITY, result.quality])
        compressed_bytes = buffer.tobytes()

        return compressed_bytes, result


def compress_image_adaptive(
    image: np.ndarray,
    original_bytes: int | None = None,
) -> CompressionResult:
    """
    Удобная функция для адаптивного сжатия.

    Args:
        image: BGR изображение
        original_bytes: Размер оригинала в байтах

    Returns:
        CompressionResult
    """
    compressor = ImageCompressor(adaptive=True)
    return compressor.compress(image, original_bytes)


def compress_image_fixed(
    image: np.ndarray,
    max_dimension: int = 2200,
    quality: int = 85,
) -> CompressionResult:
    """
    Удобная функция для сжатия с фиксированными настройками.

    Args:
        image: BGR изображение
        max_dimension: Максимальный размер стороны
        quality: Качество JPEG

    Returns:
        CompressionResult
    """
    compressor = ImageCompressor(max_dimension=max_dimension, quality=quality, adaptive=False)
    return compressor.compress(image)


# === Test ===
if __name__ == "__main__":
    import sys
    from pathlib import Path

    _SCRIPT_DIR = Path(__file__).parent
    _PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent.parent

    receipts = [
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_1867.jpeg"),
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_3017.jpeg"),
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_1292.jpeg"),
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_1442.jpeg"),
    ]

    print("=" * 70)
    print("Image Compressor Testing")
    print("=" * 70)

    compressor = ImageCompressor(adaptive=True)

    for store, receipt in receipts:
        if not receipt.exists():
            print(f"Файл не найден: {receipt}")
            continue

        print(f"\n{store}: {receipt.name}")
        print("-" * 50)

        # Читаем изображение
        with open(receipt, "rb") as f:
            image_bytes = f.read()

        image = cv2.imread(str(receipt))
        h, w = image.shape[:2]
        size_kb = len(image_bytes) / 1024

        print(f"  Оригинал: {w}x{h}, {size_kb:.1f} KB")

        # Сжимаем
        result = compressor.compress(image, original_bytes=len(image_bytes))

        if result.was_compressed:
            comp_w, comp_h = result.compressed_size
            comp_kb = result.compressed_bytes / 1024
            ratio = comp_kb / size_kb * 100
            print(f"  Сжато:    {comp_w}x{comp_h}, {comp_kb:.1f} KB ({ratio:.0f}%)")
            print(f"  Метод:    {result.method}, scale={result.scale_factor:.2f}, quality={result.quality}")
        else:
            print("  Сжатие не требуется")

    print("\n" + "=" * 70)
