"""
Abstract Base Strategy для Stage 3 Selector.

Каждая стратегия знает пороги для конкретного магазина/локали
и принимает решение по обработке на основе метрик И качества съёмки.

ДВУМЕРНАЯ СИСТЕМА:
1. Магазин (Shop) → определяет пороги
2. Качество съёмки (QualityLevel) → определяет интенсивность

Паттерн "Врач-Диагност": 
- Получает метрики (анализы)
- Получает диагноз качества (BAD/LOW/MEDIUM/HIGH)
- Сравнивает с нормами для своего контекста
- Выписывает рецепт (план фильтров)
- Не прикасается к изображению (работает только с цифрами)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from loguru import logger


class AbstractStrategy(ABC):
    """
    Базовая стратегия для принятия решений о фильтрах.
    
    Каждая стратегия определяет пороги для своего контекста (магазина, локали).
    Решение зависит от ДВУХ параметров: магазина и качества съёмки.
    """
    
    # Пороги - определяются в подклассах
    BLUE_DOMINANCE_THRESHOLD: float = 20.0
    LOW_CONTRAST_THRESHOLD: float = 40.0
    CLAHE_CONTRAST_THRESHOLD: float = 50.0
    DENOISE_NOISE_THRESHOLD: float = 1000.0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Имя стратегии (для логирования)."""
        pass
    
    def decide(
        self, 
        metrics: Dict[str, float],
        quality: Optional[str] = None
    ) -> List[str]:
        """
        Принимает решение о плане фильтров на основе метрик И качества.
        
        Args:
            metrics: Dict с ключами brightness, contrast, noise, blue_dominance
            quality: QualityLevel (BAD/LOW/MEDIUM/HIGH) или None
            
        Returns:
            List[str] с фильтрами для применения
        """
        plan = []
        
        logger.debug(
            f"[Stage 3 - {self.name}] Входные данные: "
            f"quality={quality}, metrics={metrics}"
        )
        
        # 1. Выбор метода Grayscale (решение проблемы синих чернил)
        if metrics["blue_dominance"] > self.BLUE_DOMINANCE_THRESHOLD:
            plan.append("red_channel_grayscale")
            logger.debug(
                f"[Stage 3 - {self.name}] Синие чернила (diff={metrics['blue_dominance']:.1f}) "
                f"→ Red Channel (threshold={self.BLUE_DOMINANCE_THRESHOLD})"
            )
        elif metrics["contrast"] < self.LOW_CONTRAST_THRESHOLD:
            plan.append("blue_channel_grayscale")
            logger.debug(
                f"[Stage 3 - {self.name}] Низкий контраст ({metrics['contrast']:.1f}) "
                f"→ Blue Channel (threshold={self.LOW_CONTRAST_THRESHOLD})"
            )
        else:
            plan.append("standard_grayscale")
            logger.debug(f"[Stage 3 - {self.name}] Стандартное преобразование")
        
        # 2. Улучшения (Enhancements) - зависят от качества
        if self._should_apply_clahe(metrics, quality):
            plan.append("clahe")
            logger.debug(
                f"[Stage 3 - {self.name}] CLAHE: контраст={metrics['contrast']:.1f} "
                f"< threshold={self.CLAHE_CONTRAST_THRESHOLD} (quality={quality})"
            )
        
        if self._should_apply_denoise(metrics, quality):
            plan.append("denoise")
            logger.debug(
                f"[Stage 3 - {self.name}] Denoise: шум={metrics['noise']:.0f} "
                f"> threshold={self.DENOISE_NOISE_THRESHOLD} (quality={quality})"
            )
        
        logger.info(
            f"[Stage 3 - {self.name}] Решение: {plan} "
            f"(quality={quality}, metrics={metrics})"
        )
        return plan
    
    def _should_apply_clahe(
        self, 
        metrics: Dict[str, float],
        quality: Optional[str]
    ) -> bool:
        """Нужно ли применять CLAHE (зависит от метрик и качества)."""
        # Базовое правило: низкий контраст
        if metrics["contrast"] < self.CLAHE_CONTRAST_THRESHOLD:
            return True
        
        # Если качество BAD/LOW - более агрессивно применяем CLAHE
        if quality in ("bad", "low"):
            return metrics["contrast"] < (self.CLAHE_CONTRAST_THRESHOLD + 10)
        
        return False
    
    def _should_apply_denoise(
        self,
        metrics: Dict[str, float],
        quality: Optional[str]
    ) -> bool:
        """Нужно ли применять Denoise (зависит от метрик и качества)."""
        # Базовое правило: высокий шум
        if metrics["noise"] > self.DENOISE_NOISE_THRESHOLD:
            return True
        
        # Если качество BAD/LOW - более агрессивно применяем denoise
        if quality in ("bad", "low"):
            return metrics["noise"] > (self.DENOISE_NOISE_THRESHOLD - 200)
        
        return False
