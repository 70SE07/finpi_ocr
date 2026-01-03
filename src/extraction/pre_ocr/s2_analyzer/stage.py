"""
Stage 2: Analyzer (Анализатор).

Вычисляет метрики качества СЖАТОГО изображения.
На основе этих метрик Stage 3 (Selector) выбирает стратегию обработки.

КОНТРАКТЫ:
  Выходные: ImageMetrics (с гарантиями что все метрики валидны, не NaN/Inf)

Входные данные:
- image: np.ndarray (BGR, СЖАТОЕ изображение из Stage 0 и Stage 1)

Выходные данные:
- metrics: ImageMetrics с ключами:
  - brightness: яркость (0-255)
  - contrast: контраст (RMS)
  - noise: шум/резкость (Laplacian variance)
  - blue_dominance: разница синего и красного каналов
"""

import cv2
import numpy as np
from pydantic import ValidationError
from loguru import logger

from src.domain.contracts import ImageMetrics, ContractValidationError


class ImageAnalyzerStage:
    """
    Stage 2: Analyzer (Анализатор).

    Вычисляет метрики качества СЖАТОГО изображения.
    На основе этих метрик Stage 3 (Selector) выбирает стратегию обработки.
    """
    
    def __init__(self):
        logger.debug("[Stage 2: Analyzer] Инициализирован")

    def analyze(self, image: np.ndarray):
        """
        Анализирует СЖАТОЕ изображение и возвращает метрики.
        
        ВОЗВРАЩАЕТ: Гарантированный валидный ImageMetrics контракт
        
        Args:
            image: np.ndarray (BGR, уже сжатое)
            
        Returns:
            ImageMetrics с валидированными метриками качества
            
        Raises:
            ContractValidationError: если расчёты привели к невалидным значениям (NaN, Inf)
        """
        # Временная конвертация для анализа (не влияет на выходной поток)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Основные метрики
        mean_brightness = np.mean(gray)
        std_contrast = gray.std() # RMS Contrast
        
        # Оценка шума/резкости (Laplacian Variance)
        # Низкое значение (<100) = размыто, Высокое (>1000) = шумно или очень резко
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Анализ каналов для детекции цветных чернил (Blue Ink Paradox)
        # BGR формат
        b, g, r = cv2.split(image)
        b_mean = np.mean(b)
        r_mean = np.mean(r)
        
        # Если синий канал значительно ярче красного, возможно это синие чернила на белой бумаге
        blue_dominance = b_mean - r_mean

        logger.debug(
            f"[Stage 2] Метрики (сжатое изображение): "
            f"brightness={mean_brightness:.0f}, "
            f"contrast={std_contrast:.1f}, "
            f"noise={laplacian_var:.0f}, "
            f"blue_dominance={blue_dominance:.1f}"
        )

        # ✅ ВАЛИДАЦИЯ выходного контракта
        try:
            h, w = image.shape[:2]
            metrics = ImageMetrics(
                brightness=float(mean_brightness),
                contrast=float(std_contrast),
                noise=float(laplacian_var),
                blue_dominance=float(blue_dominance),
                image_width=w,
                image_height=h
            )
        except ValidationError as e:
            raise ContractValidationError("S2", "ImageMetrics", e.errors())
        
        return metrics
