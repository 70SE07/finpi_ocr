"""
Grayscale Converter для pre-OCR пайплайна.

Конвертация цветного изображения в оттенки серого:
- OCR работает с яркостью, не с цветом
- Убирает цветовой шум
- Уменьшает размер данных (1 канал вместо 3)
"""

from dataclasses import dataclass

import cv2
import numpy as np
from loguru import logger


@dataclass
class GrayscaleResult:
    """Результат конвертации в grayscale."""

    image: np.ndarray
    original_channels: int  # 1, 3 или 4
    was_converted: bool
    original_size: tuple[int, int]  # (width, height)


class GrayscaleConverter:
    """
    Конвертирует цветное изображение в оттенки серого (Grayscale).
    """

    @staticmethod
    def process(image: np.ndarray) -> GrayscaleResult:
        """
        Конвертирует изображение в grayscale.

        Args:
            image: Входное изображение (BGR, BGRA или уже grayscale)

        Returns:
            GrayscaleResult с конвертированным изображением
        """
        h, w = image.shape[:2]
        original_size = (w, h)

        # Определяем количество каналов
        if len(image.shape) == 2:
            original_channels = 1
        else:
            original_channels = image.shape[2]

        # Если уже grayscale - возвращаем как есть
        if original_channels == 1:
            logger.info(f"[Grayscale] Изображение уже в grayscale ({w}x{h})")
            return GrayscaleResult(
                image=image,
                original_channels=1,
                was_converted=False,
                original_size=original_size,
            )

        # Конвертируем: Извлекаем ТОЛЬКО Синий канал (Blue Channel)
        # BGR (Blue=0, Green=1, Red=2). Blue channel лучше всего убирает просвечивание.
        if original_channels >= 3:
            # Берем 0-й канал (Blue)
            gray = image[:, :, 0]
            logger.info(f"[Grayscale] Blue Channel Extracted (Fixes bleed-through): ({w}x{h})")
        else:
            # Fallback (не должно случиться, если original_channels != 1)
            gray = image

        logger.info(f"[Grayscale] Конвертировано: {original_channels} каналов -> 1 ({w}x{h})")

        return GrayscaleResult(
            image=gray,
            original_channels=original_channels,
            was_converted=True,
            original_size=original_size,
        )

    @staticmethod
    def to_bgr(gray_image: np.ndarray) -> np.ndarray:
        """
        Конвертирует grayscale обратно в BGR (для совместимости).

        Args:
            gray_image: Grayscale изображение

        Returns:
            BGR изображение (3 канала, но одинаковые значения)
        """
        if len(gray_image.shape) == 3:
            return gray_image  # Уже цветное

        return cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)


def convert_to_grayscale(image: np.ndarray) -> GrayscaleResult:
    """
    Удобная функция для конвертации в grayscale.

    Args:
        image: Входное изображение

    Returns:
        GrayscaleResult
    """
    converter = GrayscaleConverter()
    return converter.process(image)


# === Test ===
if __name__ == "__main__":
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
    print("Grayscale Converter Testing")
    print("=" * 70)

    converter = GrayscaleConverter()

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

        result = converter.process(image)

        gray_channels = result.image.shape[2] if len(result.image.shape) == 3 else 1
        print(f"  Grayscale: {result.original_size[0]}x{result.original_size[1]}, {gray_channels} канал")
        print(f"  Конвертировано: {result.was_converted}")

    print("\n" + "=" * 70)
