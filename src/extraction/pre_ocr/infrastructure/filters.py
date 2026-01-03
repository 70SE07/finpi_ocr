"""
Pre-OCR Infrastructure: Фильтры и операции обработки изображений.

Утилиты низкого уровня для применения различных фильтров.
"""

import cv2
import numpy as np
import numpy.typing as npt
from typing import Dict, Any


def apply_grayscale(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """Преобразует изображение в grayscale."""
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)  # type: ignore[return-value]


def apply_clahe(image: npt.NDArray[np.uint8], clip_limit: float = 2.0, tile_size: int = 8) -> npt.NDArray[np.uint8]:
    """
    CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Grayscale изображение (H, W)
        clip_limit: Threshold для контраста (default 2.0)
        tile_size: Размер локальной области (default 8)
    """
    if len(image.shape) != 2:
        image = apply_grayscale(image)
    
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    return clahe.apply(image)  # type: ignore[return-value]


def apply_denoise(image: npt.NDArray[np.uint8], strength: int = 10) -> npt.NDArray[np.uint8]:
    """
    Денойзинг (удаление шума).
    
    Args:
        image: Исходное изображение
        strength: Интенсивность (1-100, default 10)
    """
    if len(image.shape) == 2:
        return cv2.fastNlMeansDenoising(image, h=strength)  # type: ignore[return-value]
    else:
        return cv2.fastNlMeansDenoisingColored(image, h=strength)  # type: ignore[return-value]


def apply_bilateral_filter(image: npt.NDArray[np.uint8], diameter: int = 9, sigma_color: float = 75.0, sigma_space: float = 75.0) -> npt.NDArray[np.uint8]:
    """
    Bilateral Filter (сглаживание с сохранением границ).
    
    Args:
        image: Исходное изображение
        diameter: Диаметр пикселей (default 9)
        sigma_color: Стандартное отклонение по цвету (default 75.0)
        sigma_space: Стандартное отклонение по пространству (default 75.0)
    """
    return cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)  # type: ignore[return-value]


def apply_morphological_closing(image: npt.NDArray[np.uint8], kernel_size: int = 5) -> npt.NDArray[np.uint8]:
    """
    Морфологическое закрытие (замыкание маленьких отверстий).
    
    Args:
        image: Grayscale изображение
        kernel_size: Размер ядра (нечётное число)
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)  # type: ignore[return-value]


def apply_morphological_opening(image: npt.NDArray[np.uint8], kernel_size: int = 5) -> npt.NDArray[np.uint8]:
    """
    Морфологическое открытие (удаление мелкого шума).
    
    Args:
        image: Grayscale изображение
        kernel_size: Размер ядра (нечётное число)
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)  # type: ignore[return-value]


def calculate_brightness(image: npt.NDArray[np.uint8]) -> float:
    """
    Вычисляет среднюю яркость изображения.
    
    Args:
        image: BGR/RGB/Grayscale изображение
        
    Returns:
        Значение яркости (0-255)
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # type: ignore[assignment]
    mean_result = cv2.mean(image)
    # cv2.mean() возвращает tuple[float, ...], берем первый элемент
    if isinstance(mean_result, (tuple, list)):
        return float(mean_result[0])
    return float(mean_result)  # type: ignore[arg-type]


def calculate_contrast(image: npt.NDArray[np.uint8]) -> float:
    """
    Вычисляет контраст изображения (стандартное отклонение).
    
    Args:
        image: BGR/RGB/Grayscale изображение
        
    Returns:
        Значение контраста
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # type: ignore[assignment]
    return float(image.std())


def calculate_sharpness(image: npt.NDArray[np.uint8]) -> float:
    """
    Вычисляет резкость изображения (Laplacian variance).
    
    Args:
        image: BGR/RGB/Grayscale изображение
        
    Returns:
        Значение резкости
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # type: ignore[assignment]
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    return float(laplacian.var())


def calculate_histogram_entropy(image: npt.NDArray[np.uint8]) -> float:
    """
    Вычисляет энтропию гистограммы.
    
    Args:
        image: Grayscale изображение
        
    Returns:
        Значение энтропии
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # type: ignore[assignment]
    
    histogram = cv2.calcHist([image], [0], None, [256], [0, 256])
    histogram = histogram.ravel() / histogram.sum()
    
    # Entropy = -sum(p(i) * log(p(i)))
    entropy = -np.sum(histogram * np.log(histogram + 1e-10))
    return float(entropy)
