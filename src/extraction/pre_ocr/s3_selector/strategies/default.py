"""
Default Strategy - используется если магазин не определен.

Пороги основаны на глобальных settings.py значениях.
"""

from .base import AbstractStrategy
from config.settings import (
    BLUE_DOMINANCE_THRESHOLD,
    LOW_CONTRAST_THRESHOLD,
    CLAHE_CONTRAST_THRESHOLD,
    DENOISE_NOISE_THRESHOLD
)


class DefaultStrategy(AbstractStrategy):
    """
    Стратегия по умолчанию для всех магазинов.
    
    Пороги берутся из config/settings.py.
    """
    
    BLUE_DOMINANCE_THRESHOLD = BLUE_DOMINANCE_THRESHOLD
    LOW_CONTRAST_THRESHOLD = LOW_CONTRAST_THRESHOLD
    CLAHE_CONTRAST_THRESHOLD = CLAHE_CONTRAST_THRESHOLD
    DENOISE_NOISE_THRESHOLD = DENOISE_NOISE_THRESHOLD
    
    @property
    def name(self) -> str:
        return "Default"
