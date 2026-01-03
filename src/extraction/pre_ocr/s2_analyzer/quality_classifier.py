"""
Quality Classifier - классификация качества съёмки на основе метрик.

На основе измеренных метрик (brightness, contrast, noise, blue_dominance)
определяет уровень качества съёмки, независимо от того, как было снято.

Мы не знаем:
  - Какая камера
  - Когда снимали (день/ночь)
  - Освещение
  - Рука трясётся или нет
  
Но мы ИЗМЕРЯЕМ эффект всего этого через метрики!
"""

from enum import Enum
from typing import Dict
from loguru import logger

from config.settings import (
    # Пороги для BAD quality
    BRIGHTNESS_BAD_MIN,
    BRIGHTNESS_BAD_MAX,
    CONTRAST_BAD_MAX,
    NOISE_BAD_MIN,
    
    # Пороги для MEDIUM quality
    BRIGHTNESS_MEDIUM_MIN,
    BRIGHTNESS_MEDIUM_MAX,
    CONTRAST_MEDIUM_MIN,
    NOISE_MEDIUM_MAX,
    
    # Пороги для HIGH quality
    BRIGHTNESS_HIGH_MIN,
    BRIGHTNESS_HIGH_MAX,
    CONTRAST_HIGH_MIN,
    NOISE_HIGH_MAX,
)


class QualityLevel(str, Enum):
    """Уровни качества съёмки."""
    BAD = "bad"          # Критически плохое (требует максимальной обработки)
    LOW = "low"          # Плохое (требует агрессивной обработки)
    MEDIUM = "medium"    # Среднее (обычная обработка)
    HIGH = "high"        # Хорошее (минимальная обработка)


class ImageQualityClassifier:
    """
    Классификатор качества съёмки.
    
    На основе измеренных метрик определяет уровень качества.
    Мы не знаем ПРИЧИНУ (камера, свет и т.д.), но видим СИМПТОМЫ.
    """
    
    @staticmethod
    def classify(metrics: Dict[str, float]) -> QualityLevel:
        """
        Классифицирует качество съёмки.
        
        Args:
            metrics: Dict с ключами:
              - brightness: средняя яркость [0-255]
              - contrast: контраст [0-255]
              - noise: уровень шума [0-∞]
              - blue_dominance: % синего канала [0-100]
              
        Returns:
            QualityLevel: уровень качества
        """
        brightness = metrics.get('brightness', 128)
        contrast = metrics.get('contrast', 50)
        noise = metrics.get('noise', 500)
        
        logger.debug(
            f"[QualityClassifier] Анализ метрик: "
            f"brightness={brightness:.0f}, contrast={contrast:.2f}, noise={noise:.0f}"
        )
        
        # Проверяем BAD качество (критически плохое)
        if ImageQualityClassifier._is_bad_quality(brightness, contrast, noise):
            logger.debug("[QualityClassifier] Вывод: BAD quality (критически плохо)")
            return QualityLevel.BAD
        
        # Проверяем HIGH качество (хорошее)
        if ImageQualityClassifier._is_high_quality(brightness, contrast, noise):
            logger.debug("[QualityClassifier] Вывод: HIGH quality (хорошо)")
            return QualityLevel.HIGH
        
        # Проверяем MEDIUM качество (среднее)
        if ImageQualityClassifier._is_medium_quality(brightness, contrast, noise):
            logger.debug("[QualityClassifier] Вывод: MEDIUM quality (среднее)")
            return QualityLevel.MEDIUM
        
        # По умолчанию LOW (плохое)
        logger.debug("[QualityClassifier] Вывод: LOW quality (плохо)")
        return QualityLevel.LOW
    
    @staticmethod
    def _is_bad_quality(brightness: float, contrast: float, noise: float) -> bool:
        """Критически плохое качество съёмки."""
        # Слишком темно или переэкспонировано
        if brightness < BRIGHTNESS_BAD_MIN or brightness > BRIGHTNESS_BAD_MAX:
            logger.debug(
                f"[QualityClassifier] BAD: brightness={brightness} "
                f"outside [{BRIGHTNESS_BAD_MIN}, {BRIGHTNESS_BAD_MAX}]"
            )
            return True
        
        # Сильное размытие
        if contrast < CONTRAST_BAD_MAX:
            logger.debug(
                f"[QualityClassifier] BAD: contrast={contrast} < {CONTRAST_BAD_MAX} "
                "(размыто)"
            )
            return True
        
        # Очень сильный шум
        if noise > NOISE_BAD_MIN:
            logger.debug(
                f"[QualityClassifier] BAD: noise={noise} > {NOISE_BAD_MIN} "
                "(сильно зашумлено)"
            )
            return True
        
        return False
    
    @staticmethod
    def _is_high_quality(brightness: float, contrast: float, noise: float) -> bool:
        """Хорошее качество съёмки."""
        brightness_ok = (
            BRIGHTNESS_HIGH_MIN <= brightness <= BRIGHTNESS_HIGH_MAX
        )
        contrast_ok = contrast >= CONTRAST_HIGH_MIN
        noise_ok = noise <= NOISE_HIGH_MAX
        
        is_good = brightness_ok and contrast_ok and noise_ok
        
        if is_good:
            logger.debug(
                f"[QualityClassifier] HIGH: все метрики в пределах нормы "
                f"(brightness OK, contrast={contrast:.2f}>={CONTRAST_HIGH_MIN}, "
                f"noise={noise:.0f}<={NOISE_HIGH_MAX})"
            )
        
        return is_good
    
    @staticmethod
    def _is_medium_quality(brightness: float, contrast: float, noise: float) -> bool:
        """Среднее качество съёмки."""
        brightness_ok = (
            BRIGHTNESS_MEDIUM_MIN <= brightness <= BRIGHTNESS_MEDIUM_MAX
        )
        contrast_ok = contrast >= CONTRAST_MEDIUM_MIN
        noise_ok = noise <= NOISE_MEDIUM_MAX
        
        is_medium = brightness_ok and contrast_ok and noise_ok
        
        if is_medium:
            logger.debug(
                f"[QualityClassifier] MEDIUM: метрики в приемлемом диапазоне "
                f"(brightness={brightness:.0f}, contrast={contrast:.2f}, "
                f"noise={noise:.0f})"
            )
        
        return is_medium
