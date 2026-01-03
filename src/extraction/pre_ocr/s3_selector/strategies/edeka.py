"""
Edeka Strategy - супермаркеты Edeka.

Характеристики:
- Среднее качество печати (между Rewe и Aldi)
- Обычное освещение
- Контраст средний
- Сбалансированные пороги между Rewe и Aldi
"""

from .base import AbstractStrategy


class EdekaStrategy(AbstractStrategy):
    """
    Стратегия для супермаркетов Edeka.
    
    Edeka = среднее качество между Rewe и Aldi
    Сбалансированные пороги
    """
    
    # Синие чернила: 22 (между Rewe и Aldi)
    BLUE_DOMINANCE_THRESHOLD = 22.0
    
    # Низкий контраст: 42 (между Rewe 35 и Aldi 42)
    LOW_CONTRAST_THRESHOLD = 42.0
    
    # Контраст для CLAHE: 50 (дефолт)
    CLAHE_CONTRAST_THRESHOLD = 50.0
    
    # Шум для денойзирования: 1000 (дефолт)
    DENOISE_NOISE_THRESHOLD = 1000.0
    
    @property
    def name(self) -> str:
        return "Edeka"
