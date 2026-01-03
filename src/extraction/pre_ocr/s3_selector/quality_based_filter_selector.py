"""
Quality-Based Filter Selector

Выбирает фильтры на основе ТОЛЬКО качества съёмки (BAD/LOW/MEDIUM/HIGH).
Работает независимо от магазина, локали, камеры - универсально масштабируется.

КОНТРАКТЫ:
  Входные: ImageMetrics (с гарантиями валидности)
  Выходные: FilterPlan (с гарантиями валидности и порядка)

Логика:
- BAD качество (шум, темнота, низкий контраст) → максимум фильтров
- LOW качество → больше фильтров
- MEDIUM качество → умеренно
- HIGH качество → минимум (базовая обработка)
"""

from pydantic import ValidationError
from loguru import logger

from src.domain.contracts import (
    ImageMetrics, 
    FilterPlan, 
    FilterType, 
    QualityLevel,
    ContractValidationError
)


class QualityBasedFilterSelector:
    """
    Выбирает фильтры на основе классифицированного качества.
    
    Принцип: одна и та же логика работает для всех магазинов, локалей, камер.
    Шум остаётся шумом, темнота - темнотой, независимо от источника.
    """
    
    def __init__(self):
        """Инициализация селектора фильтров"""
        logger.debug("[QualityFilterSelector] Инициализирован")
        
        # Пороги для каждого уровня качества
        # Эти пороги неизменны и универсальны
        self.thresholds = {
            QualityLevel.BAD: {
                "denoise_noise_threshold": 900,      # Более агрессивный
                "clahe_contrast_threshold": 40,       # Более агрессивный
            },
            QualityLevel.LOW: {
                "denoise_noise_threshold": 1100,
                "clahe_contrast_threshold": 50,
            },
            QualityLevel.MEDIUM: {
                "denoise_noise_threshold": 1300,
                "clahe_contrast_threshold": 60,
            },
            QualityLevel.HIGH: {
                "denoise_noise_threshold": 1500,      # Не применяем
                "clahe_contrast_threshold": 80,       # Не применяем
            },
        }
    
    def select_filters(
        self,
        metrics: ImageMetrics,
        quality: QualityLevel
    ) -> FilterPlan:
        """
        Выбирает список фильтров на основе качества.
        
        ВОЗВРАЩАЕТ: Гарантированный валидный FilterPlan контракт
        
        Args:
            metrics: ImageMetrics (валидированный контракт)
            quality: QualityLevel (BAD/LOW/MEDIUM/HIGH)
        
        Returns:
            FilterPlan: список фильтров в правильном порядке
            
        Raises:
            ContractValidationError: если результат невалидный
        """
        filters = []
        
        logger.debug(
            f"[QualityFilterSelector] Входные данные: quality={quality}, "
            f"metrics=brightness={metrics.brightness:.1f}, "
            f"contrast={metrics.contrast:.2f}, "
            f"noise={metrics.noise:.2f}"
        )
        
        # Базовая обработка (для всех уровней качества)
        filters.append(FilterType.GRAYSCALE)
        logger.debug("[QualityFilterSelector] Базовое преобразование: GRAYSCALE")
        
        # Получаем пороги для текущего уровня качества
        thresholds = self.thresholds[quality]
        
        # Определяем нужен ли CLAHE (контрастирование)
        if self._should_apply_clahe(metrics, quality, thresholds):
            filters.append(FilterType.CLAHE)
            logger.debug(
                f"[QualityFilterSelector] CLAHE: контраст={metrics.contrast:.2f} "
                f"< threshold={thresholds['clahe_contrast_threshold']} (quality={quality})"
            )
        
        # Определяем нужен ли DENOISE (удаление шума)
        if self._should_apply_denoise(metrics, quality, thresholds):
            filters.append(FilterType.DENOISE)
            logger.debug(
                f"[QualityFilterSelector] Denoise: шум={metrics.noise:.2f} "
                f"> threshold={thresholds['denoise_noise_threshold']} (quality={quality})"
            )
        
        # Объясняем выбор
        reason = self._generate_reason(metrics, quality, filters)
        
        logger.info(
            f"[QualityFilterSelector] Решение: {[f.value for f in filters]} "
            f"(quality={quality.value}, metrics: "
            f"brightness={metrics.brightness:.1f}, "
            f"contrast={metrics.contrast:.2f}, "
            f"noise={metrics.noise:.2f})"
        )
        
        # ✅ ВАЛИДАЦИЯ выходного контракта
        try:
            plan = FilterPlan(
                filters=filters,
                quality_level=quality,
                reason=reason,
                metrics_snapshot={
                    "brightness": metrics.brightness,
                    "contrast": metrics.contrast,
                    "noise": metrics.noise,
                    "blue_dominance": metrics.blue_dominance
                }
            )
        except ValidationError as e:
            raise ContractValidationError("S3", "FilterPlan", e.errors())
        
        return plan
    
    def _should_apply_clahe(
        self,
        metrics: ImageMetrics,
        quality: QualityLevel,
        thresholds: dict
    ) -> bool:
        """
        Определяет нужно ли применить CLAHE (контрастирование).
        
        CLAHE нужен когда контраст ниже порога для текущего уровня качества.
        """
        threshold = thresholds["clahe_contrast_threshold"]
        return metrics.contrast < threshold
    
    def _should_apply_denoise(
        self,
        metrics: ImageMetrics,
        quality: QualityLevel,
        thresholds: dict
    ) -> bool:
        """
        Определяет нужно ли применить DENOISE (удаление шума).
        
        Denoise нужен когда шум выше порога для текущего уровня качества.
        """
        threshold = thresholds["denoise_noise_threshold"]
        return metrics.noise > threshold
    
    def _generate_reason(self, metrics: ImageMetrics, quality: QualityLevel, filters: list) -> str:
        """Генерирует человеко-читаемое объяснение выбора фильтров."""
        reasons = []
        
        if quality == QualityLevel.BAD:
            reasons.append("Критически плохое качество")
        elif quality == QualityLevel.LOW:
            reasons.append("Плохое качество")
        elif quality == QualityLevel.MEDIUM:
            reasons.append("Среднее качество")
        else:
            reasons.append("Хорошее качество")
        
        if FilterType.CLAHE in filters:
            reasons.append(f"низкий контраст ({metrics.contrast:.1f})")
        
        if FilterType.DENOISE in filters:
            reasons.append(f"высокий шум ({metrics.noise:.0f})")
        
        return " + ".join(reasons) if reasons else "Базовая обработка"
