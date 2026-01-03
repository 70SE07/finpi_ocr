"""
Pre-OCR Infrastructure: Фильтры и операции обработки изображений.

Утилиты низкого уровня для применения различных фильтров.
"""

import cv2
import numpy as np
from typing import Dict, Any


def apply_grayscale(image: np.ndarray) -> np.ndarray:
    """Преобразует изображение в grayscale."""
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8) -> np.ndarray:
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
    return clahe.apply(image)


def apply_denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """
    Денойзинг (удаление шума).
    
    Args:
        image: Исходное изображение
        strength: Интенсивность (1-100, default 10)
    """
    if len(image.shape) == 2:
        return cv2.fastNlMeansDenoising(image, h=strength)
    else:
        return cv2.fastNlMeansDenoisingColored(image, h=strength)


def apply_bilateral_filter(image: np.ndarray, diameter: int = 9, sigma_color: float = 75.0, sigma_space: float = 75.0) -> np.ndarray:
    """
    Bilateral Filter (сглаживание с сохранением границ).
    
    Args:
        image: Исходное изображение
        diameter: Диаметр пикселей (default 9)
        sigma_color: Стандартное отклонение по цвету (default 75.0)
        sigma_space: Стандартное отклонение по пространству (default 75.0)
    """
    return cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)


def apply_morphological_closing(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Морфологическое закрытие (замыкание маленьких отверстий).
    
    Args:
        image: Grayscale изображение
        kernel_size: Размер ядра (нечётное число)
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)


def apply_morphological_opening(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """
    Морфологическое открытие (удаление мелкого шума).
    
    Args:
        image: Grayscale изображение
        kernel_size: Размер ядра (нечётное число)
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)


def calculate_brightness(image: np.ndarray) -> float:
    """
    Вычисляет среднюю яркость изображения.
    
    Args:
        image: BGR/RGB/Grayscale изображение
        
    Returns:
        Значение яркости (0-255)
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.mean(image)[0])


def calculate_contrast(image: np.ndarray) -> float:
    """
    Вычисляет контраст изображения (стандартное отклонение).
    
    Args:
        image: BGR/RGB/Grayscale изображение
        
    Returns:
        Значение контраста
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(image.std())


def calculate_sharpness(image: np.ndarray) -> float:
    """
    Вычисляет резкость изображения (Laplacian variance).
    
    Args:
        image: BGR/RGB/Grayscale изображение
        
    Returns:
        Значение резкости
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    return float(laplacian.var())


def calculate_histogram_entropy(image: np.ndarray) -> float:
    """
    Вычисляет энтропию гистограммы.
    
    Args:
        image: Grayscale изображение
        
    Returns:
        Значение энтропии
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    histogram = cv2.calcHist([image], [0], None, [256], [0, 256])
    histogram = histogram.ravel() / histogram.sum()
    
    # Entropy = -sum(p(i) * log(p(i)))
    entropy = -np.sum(histogram * np.log(histogram + 1e-10))
    return float(entropy)
