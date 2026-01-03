"""
Пайплайн для домена Extraction.

Обрабатывает изображения через:
1. Preprocessing изображений
2. OCR распознавание текста

ЦКП: RawOCRResult — 100% качественный OCR результат.

ВАЖНО: Возвращает RawOCRResult из contracts/d1_extraction_dto.py
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger

from contracts.d1_extraction_dto import RawOCRResult
from ..domain.interfaces import IExtractionPipeline, IOCRProvider, IImagePreprocessor
from ..domain.exceptions import ExtractionError, ImageProcessingError, OCRProcessingError

# Импортируем конфигурацию Feedback Loop
from config.settings import (
    ENABLE_FEEDBACK_LOOP,
    MAX_RETRIES,
    CONFIDENCE_EXCELLENT_THRESHOLD,
    CONFIDENCE_ACCEPTABLE_THRESHOLD,
    CONFIDENCE_RETRY_THRESHOLD,
    CONFIDENCE_MIN_WORD_THRESHOLD,
    CONFIDENCE_MAX_LOW_RATIO,
    RETRY_LOG_DETAILS,
)


class ExtractionPipeline(IExtractionPipeline):
    """
    Пайплайн домена Extraction.
    
    Координирует:
    1. Preprocessing изображения (опционально)
    2. OCR распознавание
    
    ЦКП: RawOCRResult с full_text и words[] для D2.
    """
    
    def __init__(
        self,
        ocr_provider: IOCRProvider,
        image_preprocessor: Optional[IImagePreprocessor] = None,
        enable_feedback_loop: Optional[bool] = None
    ):
        """
        Инициализация пайплайна extraction.
        
        Args:
            ocr_provider: Провайдер OCR (GoogleVisionOCR)
            image_preprocessor: Препроцессор изображений (опционально)
            enable_feedback_loop: Включить Feedback Loop (по умолчанию из config)
        """
        self.ocr_provider = ocr_provider
        self.image_preprocessor = image_preprocessor
        self.enable_feedback_loop = enable_feedback_loop if enable_feedback_loop is not None else ENABLE_FEEDBACK_LOOP
        
        logger.info(
            f"[Extraction] Pipeline инициализирован "
            f"(Feedback Loop: {'ON' if self.enable_feedback_loop else 'OFF'})"
        )
    
    def process_image(self, image_path: Path) -> RawOCRResult:
        """
        Обрабатывает изображение через полный пайплайн extraction.
        
        Если ENABLE_FEEDBACK_LOOP = True, использует retry механизм.
        Если False, делает одну попытку без анализа confidence.
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            RawOCRResult: Контракт D1->D2 с full_text и words[]
        """
        try:
            logger.info(f"[Extraction] Обработка: {image_path.name}")
            
            # Если Feedback Loop включен, используем retry механизм
            if self.enable_feedback_loop:
                return self._process_image_with_retry(image_path)
            
            # Иначе обрабатываем без retry (legacy behavior)
            return self._process_image_single_attempt(image_path, strategy=None)
            
        except ExtractionError:
            raise
        except Exception as e:
            logger.error(f"[Extraction] Ошибка: {e}")
            raise ExtractionError(
                message=f"Ошибка при обработке: {image_path}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def _process_image_single_attempt(
        self, 
        image_path: Path, 
        strategy: Optional[Dict[str, Any]] = None
    ) -> RawOCRResult:
        """
        Обрабатывает изображение ОДНОЙ попыткой (без retry).
        
        Args:
            image_path: Путь к изображению
            strategy: Стратегия обработки (None = adaptive по умолчанию)
            
        Returns:
            RawOCRResult
        """
        # 1. Preprocessing (если есть препроцессор)
        preprocessing_applied: List[str] = []
        
        if self.image_preprocessor:
            logger.debug("[Extraction] Этап 1: Preprocessing")
            processed_image, preprocess_metadata = self._preprocess_image(image_path, strategy)
            preprocessing_applied = preprocess_metadata.get("applied", [])
        else:
            logger.debug("[Extraction] Этап 1: Preprocessing пропущен")
            with open(image_path, 'rb') as f:
                processed_image = f.read()
        
        # 2. OCR распознавание
        logger.debug("[Extraction] Этап 2: OCR")
        result = self._perform_ocr(processed_image, image_path.stem)
        
        # Добавляем информацию о preprocessing в метаданные
        if result.metadata and preprocessing_applied:
                # Создаём новый объект метаданных с обновлёнными данными
                from contracts.d1_extraction_dto import OCRMetadata
                result = RawOCRResult(
                    full_text=result.full_text,
                    words=result.words,
                    metadata=OCRMetadata(
                        source_file=result.metadata.source_file,
                        image_width=result.metadata.image_width,
                        image_height=result.metadata.image_height,
                        processed_at=result.metadata.processed_at,
                        preprocessing_applied=preprocessing_applied,
                        retry_info=None
                    )
                )
        
        logger.info(
            f"[Extraction] Готово: {image_path.name} "
            f"({len(result.words)} слов, {len(result.full_text)} символов)"
        )
        
        return result
    
    def _preprocess_image(
        self, 
        image_path: Path, 
        strategy: Optional[Dict[str, Any]] = None
    ) -> tuple[bytes, Dict[str, Any]]:
        """
        Выполняет preprocessing изображения.
        
        Args:
            image_path: Путь к изображению
            strategy: Опциональная стратегия (для retry)
        """
        try:
            if not self.image_preprocessor:
                raise ImageProcessingError(
                    message="Препроцессор не указан",
                    component="ExtractionPipeline"
                )
            
            # TODO: В будущем передавать strategy в preprocessor для изменения параметров
            # Пока что preprocessor работает адаптивно без внешних стратегий
            return self.image_preprocessor.process(image_path)
            
        except Exception as e:
            raise ImageProcessingError(
                message=f"Ошибка preprocessing: {image_path}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def _perform_ocr(self, image_content: bytes, source_file: str) -> RawOCRResult:
        """Выполняет OCR распознавание."""
        try:
            return self.ocr_provider.recognize(image_content, source_file)
            
        except Exception as e:
            raise OCRProcessingError(
                message=f"Ошибка OCR: {source_file}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def batch_process(self, image_paths: List[Path]) -> Dict[str, Any]:
        """
        Обрабатывает несколько изображений.
        
        Args:
            image_paths: Список путей к изображениям
            
        Returns:
            dict: Статистика обработки
        """
        results: Dict[str, Any] = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "results": {}
        }
        
        for image_path in image_paths:
            try:
                result = self.process_image(image_path)
                results["success"] += 1
                results["results"][image_path.name] = {
                    "status": "success",
                    "words_count": len(result.words),
                    "text_length": len(result.full_text)
                }
            except Exception as e:
                results["failed"] += 1
                results["results"][image_path.name] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            results["processed"] += 1
        
        logger.info(
            f"[Extraction] Batch: {results['success']}/{results['processed']} успешно"
        )
        
        return results
    
    # =========================================================================
    # FEEDBACK LOOP: Методы для retry механизма
    # =========================================================================
    
    def _process_image_with_retry(self, image_path: Path) -> RawOCRResult:
        """
        Обрабатывает изображение с Feedback Loop (retry механизм).
        
        Алгоритм:
        1. Попытка 1: Adaptive (по умолчанию, quality-based)
        2. Анализ confidence → если плохо → попытка 2
        3. Попытка 2: Aggressive (форсируем BAD quality, JPEG 95%)
        4. Анализ confidence → если все еще плохо → попытка 3
        5. Попытка 3: Minimal (только GRAYSCALE, PNG)
        6. Возвращаем лучший результат
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            RawOCRResult с добавленным retry_info в metadata
        """
        attempt_details = []
        best_result = None
        best_avg_confidence = 0.0
        
        # Выполняем до MAX_RETRIES попыток
        for attempt_num in range(1, MAX_RETRIES + 1):
            # Получаем стратегию для текущей попытки
            strategy = self._get_retry_strategy(attempt_num)
            strategy_name = strategy.get("name", f"attempt_{attempt_num}")
            
            logger.debug(
                f"[Feedback Loop] Попытка {attempt_num}/{MAX_RETRIES}: "
                f"стратегия '{strategy_name}'"
            )
            
            # Обрабатываем изображение
            result = self._process_image_single_attempt(image_path, strategy)
            
            # Вычисляем метрики confidence
            metrics = self._calculate_confidence_metrics(result)
            avg_conf = metrics["average_confidence"]
            min_conf = metrics["min_confidence"]
            low_conf_ratio = metrics["low_confidence_ratio"]
            
            # Сохраняем детали попытки
            attempt_details.append({
                "attempt": attempt_num,
                "strategy": strategy_name,
                "average_confidence": round(avg_conf, 4),
                "min_confidence": round(min_conf, 4),
                "low_confidence_ratio": round(low_conf_ratio, 4),
                "words_count": len(result.words)
            })
            
            # Обновляем лучший результат
            if avg_conf > best_avg_confidence:
                best_result = result
                best_avg_confidence = avg_conf
            
            # Логируем результат попытки
            if RETRY_LOG_DETAILS:
                logger.info(
                    f"[Feedback Loop] Попытка {attempt_num}: "
                    f"avg_conf={avg_conf:.3f}, min_conf={min_conf:.3f}, "
                    f"low_conf_ratio={low_conf_ratio:.2%}, words={len(result.words)}"
                )
            
            # Проверяем приемлемость результата
            is_acceptable, reason = self._is_result_acceptable(result, metrics)
            
            if is_acceptable:
                # Результат приемлемый → прекращаем retry
                logger.info(
                    f"[Feedback Loop] ✅ Результат приемлемый на попытке {attempt_num}: {reason}"
                )
                
                # Добавляем retry_info в metadata
                final_result = self._add_retry_info_to_result(
                    result, 
                    attempt_num, 
                    metrics, 
                    attempt_details, 
                    was_retried=(attempt_num > 1)
                )
                
                return final_result
            
            # Результат неприемлемый
            if attempt_num < MAX_RETRIES:
                logger.warning(
                    f"[Feedback Loop] ⚠️ Результат неприемлемый: {reason}. "
                    f"Пробуем попытку {attempt_num + 1}..."
                )
            else:
                logger.error(
                    f"[Feedback Loop] ❌ Все {MAX_RETRIES} попыток исчерпаны. "
                    f"Возвращаем лучший результат (avg_conf={best_avg_confidence:.3f})"
                )
        
        # Все попытки исчерпаны → возвращаем лучший результат
        if best_result is None:
            raise ExtractionError(
                message=f"Не удалось обработать изображение после {MAX_RETRIES} попыток",
                component="ExtractionPipeline.FeedbackLoop"
            )
        
        final_metrics = self._calculate_confidence_metrics(best_result)
        final_result = self._add_retry_info_to_result(
            best_result, 
            MAX_RETRIES, 
            final_metrics, 
            attempt_details, 
            was_retried=True,
            all_attempts_failed=True
        )
        
        return final_result
    
    def _calculate_confidence_metrics(self, result: RawOCRResult) -> Dict[str, float]:
        """
        Вычисляет метрики confidence для результата OCR.
        
        Args:
            result: RawOCRResult с words
            
        Returns:
            Dict с метриками:
            - average_confidence: средний confidence всех слов
            - min_confidence: минимальный confidence
            - max_confidence: максимальный confidence
            - low_confidence_ratio: доля слов с confidence < 0.85
        """
        if not result.words:
            return {
                "average_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "low_confidence_ratio": 1.0
            }
        
        confidences = [w.confidence for w in result.words]
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        
        # Считаем долю слов с низким confidence
        low_conf_words = [c for c in confidences if c < 0.85]
        low_conf_ratio = len(low_conf_words) / len(confidences)
        
        return {
            "average_confidence": avg_conf,
            "min_confidence": min_conf,
            "max_confidence": max_conf,
            "low_confidence_ratio": low_conf_ratio
        }
    
    def _is_result_acceptable(
        self, 
        result: RawOCRResult, 
        metrics: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Проверяет приемлемость результата OCR для финансового учета.
        
        Критерии (из PROJECT_VISION.md и config):
        1. Average confidence >= ACCEPTABLE_THRESHOLD (0.90)
        2. Min confidence >= MIN_WORD_THRESHOLD (0.70)
        3. Low confidence ratio < MAX_LOW_RATIO (0.20)
        
        Args:
            result: RawOCRResult
            metrics: Метрики confidence
            
        Returns:
            (is_acceptable, reason)
        """
        # Проверяем что есть слова
        if not result.words:
            return False, "No words recognized"
        
        avg_conf = metrics["average_confidence"]
        min_conf = metrics["min_confidence"]
        low_conf_ratio = metrics["low_confidence_ratio"]
        
        # КРИТЕРИЙ 1: Excellent confidence (сразу принимаем)
        if avg_conf >= CONFIDENCE_EXCELLENT_THRESHOLD:
            return True, f"Excellent avg_confidence={avg_conf:.3f}"
        
        # КРИТЕРИЙ 2: Average confidence
        if avg_conf < CONFIDENCE_ACCEPTABLE_THRESHOLD:
            return False, f"Low avg_confidence={avg_conf:.3f} < {CONFIDENCE_ACCEPTABLE_THRESHOLD}"
        
        # КРИТЕРИЙ 3: Minimum confidence
        if min_conf < CONFIDENCE_MIN_WORD_THRESHOLD:
            return False, f"Low min_confidence={min_conf:.3f} < {CONFIDENCE_MIN_WORD_THRESHOLD}"
        
        # КРИТЕРИЙ 4: Процент слов с низким confidence
        if low_conf_ratio > CONFIDENCE_MAX_LOW_RATIO:
            return False, f"Too many low-conf words: {low_conf_ratio:.1%} > {CONFIDENCE_MAX_LOW_RATIO:.0%}"
        
        # ✅ ВСЕ ПРОВЕРКИ ПРОШЛИ
        return True, f"Acceptable (avg={avg_conf:.3f}, min={min_conf:.3f}, low_ratio={low_conf_ratio:.1%})"
    
    def _get_retry_strategy(self, attempt_num: int) -> Dict[str, Any]:
        """
        Возвращает стратегию обработки для конкретной попытки.
        
        Стратегии:
        1. Adaptive (по умолчанию): качество-ориентированные фильтры
        2. Aggressive: форсируем максимум обработки (BAD quality, JPEG 95%)
        3. Minimal: минимум обработки (только GRAYSCALE, PNG)
        
        Args:
            attempt_num: Номер попытки (1, 2, 3, ...)
            
        Returns:
            Dict со стратегией (пока заглушка, будет использовано в будущем)
        """
        if attempt_num == 1:
            # Попытка 1: Adaptive (качество-ориентированный подход)
            return {
                "name": "adaptive",
                "description": "Quality-based adaptive preprocessing",
                # TODO: Параметры для preprocessor (в будущем)
            }
        elif attempt_num == 2:
            # Попытка 2: Aggressive (максимум обработки)
            return {
                "name": "aggressive",
                "description": "Maximum preprocessing (force BAD quality, JPEG 95%)",
                # TODO: Форсировать BAD quality, JPEG 95%, добавить SHARPEN
            }
        else:
            # Попытка 3+: Minimal (минимум обработки)
            return {
                "name": "minimal",
                "description": "Minimal preprocessing (GRAYSCALE only, PNG)",
                # TODO: Только GRAYSCALE, PNG без сжатия
            }
    
    def _add_retry_info_to_result(
        self, 
        result: RawOCRResult,
        attempts: int,
        final_metrics: Dict[str, float],
        attempt_details: List[Dict[str, Any]],
        was_retried: bool,
        all_attempts_failed: bool = False
    ) -> RawOCRResult:
        """
        Добавляет retry_info в metadata результата.
        
        Args:
            result: Исходный RawOCRResult
            attempts: Количество попыток
            final_metrics: Финальные метрики confidence
            attempt_details: Детали каждой попытки
            was_retried: Был ли retry
            all_attempts_failed: Все попытки провалились
            
        Returns:
            RawOCRResult с обновленным metadata
        """
        if not result.metadata:
            # Если metadata нет, возвращаем как есть
            return result
        
        # Формируем retry_info
        retry_info = {
            "was_retried": was_retried,
            "attempts": attempts,
            "final_avg_confidence": round(final_metrics["average_confidence"], 4),
            "final_min_confidence": round(final_metrics["min_confidence"], 4),
            "final_low_conf_ratio": round(final_metrics["low_confidence_ratio"], 4),
            "strategies_used": [detail["strategy"] for detail in attempt_details],
            "attempt_details": attempt_details,
            "all_attempts_failed": all_attempts_failed
        }
        
        # Создаем новый metadata с retry_info
        from contracts.d1_extraction_dto import OCRMetadata
        updated_metadata = OCRMetadata(
            source_file=result.metadata.source_file,
            image_width=result.metadata.image_width,
            image_height=result.metadata.image_height,
            processed_at=result.metadata.processed_at,
            preprocessing_applied=result.metadata.preprocessing_applied,
            retry_info=retry_info
        )
        
        # Создаем новый результат с обновленным metadata
        return RawOCRResult(
            full_text=result.full_text,
            words=result.words,
            metadata=updated_metadata
        )
