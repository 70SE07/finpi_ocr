"""
Адаптивный Pre-OCR Pipeline для домена Extraction.

КОНТРАКТЫ: Каждая стадия гарантирует валидность выходных данных.

6-stage оркестратор:
0. Compression: Адаптивное сжатие (CompressionRequest → CompressionResponse)
1. Preparation: Загрузка + Resize (PreparationRequest → PreparationResponse)
2. Analyzer: Вычисление метрик на СЖАТОМ изображении (→ ImageMetrics с валидацией)
3. Selector: Выбор стратегии обработки на основе метрик (ImageMetrics → FilterPlan)
4. Executor: Применение фильтров (ExecutorRequest → ExecutorResponse)
5. Encoder: Кодирование в JPEG bytes (EncoderRequest → EncoderResponse)

КРИТИЧЕСКОЕ: Compression ПЕРЕД Analyzer, чтобы метрики были адекватны размеру!
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from loguru import logger

from ..domain.interfaces import IImagePreprocessor
from .s0_compression import ImageCompressionStage
from .s1_preparation import ImagePreparationStage
from .s2_analyzer import ImageAnalyzerStage
from .s3_selector import FilterSelectorStage
from .s4_executor import ImageExecutorStage
from .s5_encoder import ImageEncoderStage
from src.domain.contracts import (
    ImageMetrics, FilterPlan, CompressionResponse, 
    ContractValidationError
)


class AdaptivePreOCRPipeline(IImagePreprocessor):
    """
    Адаптивный пайплайн препроцессинга (6 Stages) с валидационными контрактами.
    
    Stages:
    0. Compression: Адаптивное сжатие (валидированный CompressionResponse)
    1. Preparation: Load + Resize
    2. Analyzer: Calculate Metrics (валидированный ImageMetrics, no NaN/Inf)
    3. Selector: Choose Strategy (валидированный FilterPlan с гарантиями)
    4. Executor: Apply Filters
    5. Encoder: Encode to Bytes
    """
    
    def __init__(self) -> None:
        self.compression = ImageCompressionStage(mode="adaptive")
        self.preparation = ImagePreparationStage()
        self.analyzer = ImageAnalyzerStage()
        self.selector = FilterSelectorStage()  # Обновлён
        self.executor = ImageExecutorStage()
        self.encoder = ImageEncoderStage()
        logger.info("[AdaptivePreOCRPipeline] Инициализирован (6 stages, с контрактами)")

    def process(self, image_path: Path, context: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение через 6-stage пайплайн (ОПТИМИЗИРОВАННЫЙ).
        
        ОПТИМИЗАЦИЯ: 
        - Stage 0 (Compression) ПЕРВЫЙ: вычисляет целевой размер БЕЗ загрузки
        - Stage 1 (Preparation) ВТОРОЙ: загружает сразу в целевом размере
        - Экономит 60% памяти (не загружаем полный образ перед сжатием)
        
        ВАЛИДАЦИЯ: На каждой стадии выходные данные валидируются через контракты.
        Если контракт нарушен, выбрасывается ContractValidationError с деталями.
        
        Args:
            image_path: Путь к файлу изображения
            context: Dict с контекстом для Stage 3 Selector (опционально):
              - shop: str - название магазина (ИГНОРИРУЕТСЯ, используется только качество)
              - material: str - материал чека (опционально)
              - lighting: str - качество освещения (опционально)
              - device: str - модель устройства (опционально)
              
        Returns:
            (image_bytes, metadata)
            - image_bytes: JPEG bytes для отправки в Google Vision API
            - metadata: Dict с метаданными обработки (включая filter_plan, metrics)
            
        Raises:
            ContractValidationError: если какой-либо контракт нарушен
        """
        context = context or {}
        
        logger.debug(f"[AdaptivePreOCRPipeline] Обработка: {image_path.name}")
        
        # Stage 0 ПЕРВЫЙ: Compression (compute target size БЕЗ загрузки!)
        logger.debug("[AdaptivePreOCRPipeline] Stage 0: Compression (compute target size)")
        
        # Получаем размер файла и исходный размер изображения БЕЗ полной загрузки
        import os
        from PIL import Image as PILImage
        
        try:
            file_size = os.path.getsize(image_path)
            with PILImage.open(image_path) as pil_img:
                orig_w, orig_h = pil_img.size
        except Exception as e:
            logger.error(f"[AdaptivePreOCRPipeline] Ошибка чтения файла: {e}")
            raise
        
        # Вычисляем целевой размер (БЕЗ загрузки полного изображения!)
        # ✅ ВАЛИДАЦИЯ: compute_target_size проверит параметры
        target_size = self.compression.compute_target_size(orig_w, orig_h, file_size)
        logger.debug(f"[AdaptivePreOCRPipeline] Target size: {orig_w}x{orig_h} → {target_size[0]}x{target_size[1]}")
        
        # Stage 1: Preparation (Load + Resize в целевой размер)
        # ОПТИМИЗАЦИЯ: передаем target_size, загружаем сразу сжатым
        logger.debug("[AdaptivePreOCRPipeline] Stage 1: Preparation (load in target size)")
        image = self.preparation.process(image_path, target_size=target_size)
        
        # Stage 0 ВТОРОЙ: Compress (сжимаем уже загруженное в целевом размере)
        logger.debug("[AdaptivePreOCRPipeline] Stage 0: Compression (compress)")
        comp_result = self.compression.compress(image, file_size)
        image = comp_result.image
        compressed_size = comp_result.compressed_size
        compression_quality = comp_result.quality
        compression_metadata = comp_result.metadata

        # ✅ ВАЛИДАЦИЯ: compression_metadata содержит валидированный CompressionResponse
        if "response_contract" in compression_metadata:
            logger.debug(f"[AdaptivePreOCRPipeline] S0 контракт валидирован: {compression_metadata['response_contract']}")

        # Stage 2: Analyzer (на СЖАТОМ изображении!)
        # ✅ ВАЛИДАЦИЯ: analyze() возвращает валидированный ImageMetrics (не Dict!)
        logger.debug("[AdaptivePreOCRPipeline] Stage 2: Analyzer")
        try:
            metrics: ImageMetrics = self.analyzer.analyze(image)
            logger.debug(f"[AdaptivePreOCRPipeline] S2 метрики валидированы: "
                        f"brightness={metrics.brightness:.1f}, "
                        f"contrast={metrics.contrast:.2f}, "
                        f"noise={metrics.noise:.0f}")
        except ContractValidationError as e:
            logger.error(f"[AdaptivePreOCRPipeline] ❌ S2 контракт нарушен: {e}")
            raise

        # Stage 3: Selector (теперь работает только с качеством, без магазинов!)
        # ✅ ВАЛИДАЦИЯ: select_filters() возвращает валидированный FilterPlan
        logger.debug("[AdaptivePreOCRPipeline] Stage 3: Selector (качество-ориентированный)")
        try:
            filter_plan: FilterPlan = self.selector.select_filters(metrics)
            logger.debug(f"[AdaptivePreOCRPipeline] S3 план фильтров валидирован: "
                        f"{[f.value for f in filter_plan.filters]} "
                        f"(quality={filter_plan.quality_level.value}, reason={filter_plan.reason})")
        except ContractValidationError as e:
            logger.error(f"[AdaptivePreOCRPipeline] ❌ S3 контракт нарушен: {e}")
            raise

        # Stage 4: Executor (применение фильтров из плана)
        logger.debug("[AdaptivePreOCRPipeline] Stage 4: Executor")
        # ✅ Передаём FilterPlan напрямую (executor преобразует в FilterType enum)
        processed_image = self.executor.execute(image, filter_plan)

        # Stage 5: Encoder (с адаптивным качеством)
        logger.debug("[AdaptivePreOCRPipeline] Stage 5: Encoder")
        image_bytes = self.encoder.encode(processed_image, quality=compression_quality, image_size=compressed_size)

        # Формируем metadata для ExtractionPipeline
        # ВАЖНО: Ключ "applied" а не "preprocessing_plan"!
        metadata = {
            "applied": [f.value for f in filter_plan.filters],  # ← Для совместимости конвертируем в строки
            "metrics": {
                "brightness": metrics.brightness,
                "contrast": metrics.contrast,
                "noise": metrics.noise,
                "blue_dominance": metrics.blue_dominance,
                "quality_level": filter_plan.quality_level.value
            },
            "filter_plan": {
                "filters": [f.value for f in filter_plan.filters],
                "reason": filter_plan.reason,
                "quality": filter_plan.quality_level.value
            },
            "compression_metadata": compression_metadata,
            "preprocessing_quality": compression_quality
        }
        
        logger.info(
            f"[AdaptivePreOCRPipeline] ✅ Готово: {image_path.name} "
            f"(сжато {comp_result.original_size} → {compressed_size}, "
            f"качество={filter_plan.quality_level.value}, "
            f"фильтры={[f.value for f in filter_plan.filters]})"
        )
        
        return image_bytes, metadata
