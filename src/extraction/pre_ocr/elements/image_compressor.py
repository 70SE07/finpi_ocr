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
from pathlib import Path

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
    - Остальные = 2200px (стандарт)
    """

    def __init__(self, mode: Literal["adaptive", "fixed", "none"] = "adaptive"):
        """
        Args:
            mode: Режим сжатия
                - adaptive: Автоматический выбор размера
                - fixed: Фиксированный MAX_IMAGE_SIZE
                - none: Без изменения размера
        """
        self.mode = mode

    def compress(self, image: np.ndarray, original_bytes: int) -> CompressionResult:
        """
        Сжимает изображение с учетом его геометрии.

        Args:
            image: Входное изображение (numpy array)
            original_bytes: Размер оригинала в байтах

        Returns:
            CompressionResult с сжатым изображением и метаданными
        """
        h, w = image.shape[:2]
        original_size = (w, h)
        density = original_bytes / (w * h)  # байт/пиксель

        # Определяем целевой размер
        if self.mode == "none":
            target_size = (w, h)
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

        # Если изменение размера не требуется
        if method != "none" and scale_factor >= 1.0:
            logger.info(f"[Compressor] Изображение уже <= целевого размера ({w}x{h})")
            return CompressionResult(
                image=image,
                original_size=original_size,
                compressed_size=original_size,
                original_bytes=original_bytes,
                compressed_bytes=original_bytes,
                scale_factor=1.0,
                quality=100,
                method="none",
                was_compressed=False
            )

        # Ресайзим
        if method != "none":
            compressed = cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
            logger.info(f"[Compressor] {method} resize: {w}x{h} -> {target_size[0]}x{target_size[1]} (x{scale_factor:.2f})")
        else:
            compressed = image

        # Сжимаем в JPEG (для оценки размера)
        _, buffer = cv2.imencode(".jpg", compressed, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        compressed_bytes = len(buffer.tobytes())

        compression_ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0
        logger.info(f"[Compressor] Original: {original_bytes} bytes, Compressed: {compressed_bytes} bytes ({compression_ratio:.2%})")

        return CompressionResult(
            image=compressed,
            original_size=original_size,
            compressed_size=target_size,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            scale_factor=scale_factor,
            quality=JPEG_QUALITY,
            method=method,
            was_compressed=(method != "none")
        )

    def _get_fixed_size(self, w: int, h: int) -> tuple[int, int]:
        """Возвращает фиксированный размер с сохранением aspect ratio."""
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

    def _get_adaptive_size(self, w: int, h: int, density: float) -> tuple[int, int]:
        """Возвращает адаптивный размер на основе геометрии и плотности."""
        max_allowed = MAX_IMAGE_SIZE

        # Проверяем адаптивные правила
        long_receipt = h / w > ADAPTIVE_HEIGHT_RATIO
        high_density = density > ADAPTIVE_DENSITY_THRESHOLD

        if long_receipt:
            # Длинный чек - мелкие цены
            target = ADAPTIVE_LONG_RECEIPT_SIZE
            logger.info(f"[Compressor] Long receipt detected (H/W={h/w:.2f}) -> {target}px")
        elif high_density:
            # Высокая плотность - консервативно
            target = ADAPTIVE_HIGH_DENSITY_SIZE
            logger.info(f"[Compressor] High density detected ({density:.3f} b/px) -> {target}px")
        else:
            # Стандарт
            target = MAX_IMAGE_SIZE

        # Применяем с сохранением aspect ratio
        return self._get_fixed_size_by_target(w, h, target)

    def _get_fixed_size_by_target(self, w: int, h: int, target: int) -> tuple[int, int]:
        """Возвращает размер с заданным максимумом."""
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


# === Test ===
if __name__ == "__main__":
    from pathlib import Path

    _SCRIPT_DIR = Path(__file__).parent.parent.parent.parent
    _PROJECT_ROOT = _SCRIPT_DIR.parent.parent

    receipts = [
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_1867.jpeg"),
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_3017.jpeg"),
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_1292.jpeg"),
        ("Lidl", _PROJECT_ROOT / "photo/GOODS/Lidl/IMG_1442.jpeg"),
    ]

    print("=" * 70)
    print("Image Compressor Testing")
    print("=" * 70)

    compressor = ImageCompressor(mode="adaptive")

    for store, receipt in receipts:
        if not receipt.exists():
            print(f"Файл не найден: {receipt}")
            continue

        print(f"\n{store}: {receipt.name}")
        print("-" * 50)

        image = cv2.imread(str(receipt))
        h, w = image.shape[:2]
        channels = image.shape[2] if len(image.shape) == 3 else 1

        print(f"  Оригинал: {w}x{h}, {channels} каналов")

        with open(receipt, "rb") as f:
            original_bytes = len(f.read())

        result = compressor.compress(image, original_bytes)

        print(f"  Compressed: {result.compressed_size[0]}x{result.compressed_size[1]}")
        print(f"  Scale: x{result.scale_factor:.2f}")
        print(f"  Quality: {result.quality}%")
        print(f"  Size: {result.original_bytes} -> {result.compressed_bytes} bytes")
        print(f"  Method: {result.method}")

    print("\n" + "=" * 70)


