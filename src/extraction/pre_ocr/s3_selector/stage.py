"""
Stage 3: Filter Selector (Мозг).

Принимает решение о фильтрах на основе ТОЛЬКО качества съёмки.
Работает независимо от магазина, локали, модели камеры - универсально масштабируется.

КАЧЕСТВО-ОРИЕНТИРОВАННАЯ СИСТЕМА:
────────────────────────────────────────────────────────────────────────────────
Входные данные:
- metrics: Dict с ключами brightness, contrast, noise, blue_dominance

Шаг 1: КЛАССИФИКАЦИЯ КАЧЕСТВА СЪЁМКИ
  metrics → QualityClassifier → QualityLevel (BAD/LOW/MEDIUM/HIGH)
  
  Принцип: мы анализируем СИМПТОМЫ фото (шум, яркость, контраст),
  не причины (магазин, камера, освещение).

Шаг 2: ВЫБОР ФИЛЬТРОВ НА ОСНОВЕ КАЧЕСТВА
  (metrics, quality) → QualityBasedFilterSelector → plan
  
  - BAD качество → максимум фильтров (денойз + контраст)
  - LOW качество → больше фильтров
  - MEDIUM качество → умеренно
  - HIGH качество → минимум (только граyscale)

Выходные данные:
- plan: List[str] с фильтрами для Stage 4 Executor
  - "standard_grayscale" (всегда)
  - "clahe" (если low contrast)
  - "denoise" (если high noise)

ПОЧЕМУ БЕЗ МАГАЗИНОВ:
- ✅ Шум = шум (независимо от магазина)
- ✅ Темнота = темнота (независимо от локали)
- ✅ Контраст = контраст (независимо от камеры)
- ✅ Масштабируется на 1000+ магазинов автоматически
- ✅ Нет комбинаторного взрыва (магазины × локали)

ПАТТЕРН "Врач-Диагност":
- Selector = Врач (смотрит на симптомы, выписывает рецепт)
- QualityClassifier = Лабораторный анализ (диагностирует состояние)
- QualityBasedFilterSelector = Протокол лечения (одинаков для всех)
- Executor = Фармацевт (молча следует рецепту)

Один универсальный алгоритм работает для всех условий!
"""

from typing import Dict, List, Optional
from loguru import logger

from ..domain.interfaces import ISelectorStage
from ..s2_analyzer.quality_classifier import ImageQualityClassifier, QualityLevel
from .quality_based_filter_selector import QualityBasedFilterSelector
from src.domain.contracts import ImageMetrics, FilterPlan


class FilterSelectorStage(ISelectorStage):
    """
    Stage 3: Filter Selector (Мозг).
    
    Выбирает фильтры на основе ТОЛЬКО качества съёмки.
    Универсальное решение для всех магазинов, локалей, камер.
    
    КОНТРАКТЫ:
      Входные: ImageMetrics (валидированный)
      Выходные: FilterPlan (валидированный)
    """
    
    def __init__(self):
        self.quality_classifier = ImageQualityClassifier()
        self.filter_selector = QualityBasedFilterSelector()
        logger.debug("[Stage 3: Filter Selector] Инициализирован (качество-ориентированная система, с контрактами)")

    def select_filters(
        self, 
        metrics: ImageMetrics
    ) -> FilterPlan:
        """
        Выбирает план фильтров на основе качества съёмки.
        
        ВОЗВРАЩАЕТ: Гарантированный валидный FilterPlan контракт
        
        Args:
            metrics: ImageMetrics (валидированный контракт из Stage 2)
              - brightness: 0-255
              - contrast: RMS контраст
              - noise: Laplacian variance (шум/резкость)
              - blue_dominance: разница синего и красного каналов
              
        Returns:
            FilterPlan: список фильтров в правильном порядке с гарантиями
        """
        # ШАГ 1: Классифицируем качество съёмки на основе метрик
        # Преобразуем ImageMetrics обратно в Dict для классификатора
        metrics_dict = {
            "brightness": metrics.brightness,
            "contrast": metrics.contrast,
            "noise": metrics.noise,
            "blue_dominance": metrics.blue_dominance
        }
        
        quality = self.quality_classifier.classify(metrics_dict)
        
        logger.debug(
            f"[Stage 3] Качество съёмки: {quality} "
            f"(metrics: brightness={metrics.brightness:.0f}, "
            f"contrast={metrics.contrast:.2f}, "
            f"noise={metrics.noise:.0f})"
        )
        
        # ШАГ 2: Выбираем фильтры на основе ТОЛЬКО качества
        # ✅ ВАЛИДАЦИЯ: select_filters вернёт валидный FilterPlan
        filter_plan = self.filter_selector.select_filters(metrics, quality)
        
        logger.info(
            f"[Stage 3] Финальный план: {[f.value for f in filter_plan.filters]} "
            f"(quality={filter_plan.quality_level}, reason={filter_plan.reason})"
        )
        
        return filter_plan
    
    # Старый интерфейс для совместимости (оставляю на случай переходного периода)
    def select_plan(
        self, 
        metrics: Dict[str, float],
        context: Optional[Dict] = None
    ) -> List[str]:
        """
        DEPRECATED: Используй select_filters() вместо этого.
        
        Этот метод оставлен для совместимости. 
        Он преобразует Dict в ImageMetrics и вызывает select_filters().
        """
        logger.warning("[Stage 3] select_plan() deprecated - используй select_filters()")
        
        # Преобразуем Dict в ImageMetrics
        # Берём размеры из метрик или используем значения по умолчанию
        metrics_obj = ImageMetrics(
            brightness=metrics.get('brightness', 128),
            contrast=metrics.get('contrast', 50),
            noise=metrics.get('noise', 500),
            blue_dominance=metrics.get('blue_dominance', 0),
            image_width=metrics.get('image_width', 2400),
            image_height=metrics.get('image_height', 1800)
        )
        
        filter_plan = self.select_filters(metrics_obj)
        return [f.value for f in filter_plan.filters]


# Алиас для обратной совместимости (если где-то используется старое имя)
StrategySelectorStage = FilterSelectorStage

