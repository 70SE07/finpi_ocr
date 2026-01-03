"""
Stage 4: Executor (Руки).

Применяет фильтры согласно плану.

КОНТРАКТЫ:
  Входные: FilterPlan (валидированный, GRAYSCALE первый)
  Выходные: ExecutorResponse (валидированный, width/height > 0)

Входные данные:
- image: np.ndarray (BGR, сжатое изображение)
- filter_plan: FilterPlan (валидированный контракт из Stage 3)

Выходные данные:
- image: np.ndarray (Grayscale, обработанное)

ВАЖНО: Все параметры cv2 функций вынесены в config/settings.py для системности
и возможности A/B тестирования и локализации
"""

import cv2
import numpy as np
import numpy.typing as npt
import time
from typing import List, Union
from pydantic import ValidationError
from loguru import logger

from config.settings import (
    DENOISE_STRENGTH,
    DENOISE_TEMPLATE_SIZE,
    DENOISE_SEARCH_SIZE,
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_SIZE
)
from src.domain.contracts import (
    FilterType, FilterPlan, ExecutorResponse,
    ContractValidationError
)


class ImageExecutorStage:
    """
    Stage 4: Executor (Руки).

    Применяет фильтры согласно плану.
    
    КОНТРАКТЫ:
      Входные: FilterPlan (FilterType enum, GRAYSCALE first)
      Выходные: ExecutorResponse (validated dimensions, applied_filters)
    """
    
    def __init__(self) -> None:
        logger.debug("[Stage 4: Executor] Инициализирован (с контрактами)")

    def execute(
        self, 
        image: npt.NDArray[np.uint8], 
        filter_plan: Union[FilterPlan, List[str]]
    ) -> npt.NDArray[np.uint8]:
        """
        Применяет фильтры согласно плану.
        
        ВОЗВРАЩАЕТ: Обработанное Grayscale изображение (валидированное)
        
        Args:
            image: np.ndarray (BGR)
            filter_plan: FilterPlan (контракт) или List[str] (для совместимости)
            
        Returns:
            np.ndarray (Grayscale, обработанное)
            
        Raises:
            ContractValidationError: если результат невалидный
        """
        start_time = time.time()
        
        # Преобразуем List[str] в FilterType для совместимости
        if isinstance(filter_plan, list):
            filters = [FilterType(f) if isinstance(f, str) else f for f in filter_plan]
            logger.warning("[Stage 4] Получен List[str] вместо FilterPlan - конвертирую")
        else:
            filters = filter_plan.filters
        
        logger.debug(f"[Stage 4] Начало обработки: {len(filters)} фильтров")
        
        # ✅ ПРОВЕРКА: первый фильтр ДОЛЖЕН быть GRAYSCALE
        if not filters or filters[0] != FilterType.GRAYSCALE:
            raise ValueError(f"Первый фильтр должен быть GRAYSCALE, получено: {filters[0] if filters else 'пусто'}")
        
        processed = image.copy()
        applied_filters: List[FilterType] = []

        # 1. Grayscale Conversion (Обязательный шаг)
        logger.debug(f"[Stage 4] Применяю {filters[0].value}")
        processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)  # type: ignore[assignment]
        applied_filters.append(filters[0])

        # 2. Дополнительные фильтры (в порядке из плана)
        for filter_type in filters[1:]:
            if filter_type == FilterType.CLAHE:
                logger.debug(
                    f"[Stage 4] Применяю CLAHE "
                    f"(clipLimit={CLAHE_CLIP_LIMIT}, tileSize={CLAHE_TILE_SIZE}x{CLAHE_TILE_SIZE})"
                )
                clahe = cv2.createCLAHE(
                    clipLimit=CLAHE_CLIP_LIMIT,
                    tileGridSize=(CLAHE_TILE_SIZE, CLAHE_TILE_SIZE)
                )
                processed = clahe.apply(processed)  # type: ignore[assignment]
                applied_filters.append(filter_type)
            
            elif filter_type == FilterType.DENOISE:
                logger.debug(
                    f"[Stage 4] Применяю Denoise "
                    f"(h={DENOISE_STRENGTH}, template={DENOISE_TEMPLATE_SIZE}, search={DENOISE_SEARCH_SIZE})"
                )
                result = cv2.fastNlMeansDenoising(
                    processed, None,
                    DENOISE_STRENGTH,
                    DENOISE_TEMPLATE_SIZE,
                    DENOISE_SEARCH_SIZE
                )
                
                # ✅ ПРОВЕРКА: denoise должен вернуть валидный результат
                if result is None:
                    raise ValueError("cv2.fastNlMeansDenoising вернул None")
                
                processed = result  # type: ignore[assignment]
                applied_filters.append(filter_type)
            
            elif filter_type == FilterType.SHARPEN:
                logger.debug("[Stage 4] Применяю SHARPEN")
                kernel = np.array([[-1, -1, -1],
                                 [-1,  9, -1],
                                 [-1, -1, -1]])
                processed = cv2.filter2D(processed, -1, kernel)  # type: ignore[assignment]
                applied_filters.append(filter_type)
            
            else:
                logger.warning(f"[Stage 4] Неизвестный фильтр: {filter_type}, пропускаю")

        # ✅ ВАЛИДАЦИЯ выходного контракта
        execution_time_ms = (time.time() - start_time) * 1000
        
        try:
            response = ExecutorResponse(
                image_data=processed.tobytes(),  # Сохраняем для контракта
                width=processed.shape[1],
                height=processed.shape[0],
                applied_filters=applied_filters,
                processing_time_ms=execution_time_ms
            )
        except ValidationError as e:
            raise ContractValidationError("S4", "ExecutorResponse", e.errors())
        
        logger.debug(f"[Stage 4] ✅ Обработка завершена: {response.width}x{response.height}, "
                    f"фильтры={[f.value for f in applied_filters]}, "
                    f"время={execution_time_ms:.0f}ms")
        
        return processed

