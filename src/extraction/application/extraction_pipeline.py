"""
Пайплайн для домена Extraction.

Обрабатывает изображения через:
1. Preprocessing изображений
2. OCR распознавание текста

ЦКП: RawOCRResult — 100% качественный OCR результат.

ВАЖНО: Возвращает RawOCRResult из contracts/d1_extraction_dto.py
"""

from pathlib import Path
from typing import Optional, List
from loguru import logger

from contracts.d1_extraction_dto import RawOCRResult
from ..domain.interfaces import IExtractionPipeline, IOCRProvider, IImagePreprocessor
from ..domain.exceptions import ExtractionError, ImageProcessingError, OCRProcessingError


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
        image_preprocessor: Optional[IImagePreprocessor] = None
    ):
        """
        Инициализация пайплайна extraction.
        
        Args:
            ocr_provider: Провайдер OCR (GoogleVisionOCR)
            image_preprocessor: Препроцессор изображений (опционально)
        """
        self.ocr_provider = ocr_provider
        self.image_preprocessor = image_preprocessor
        
        logger.info("[Extraction] Pipeline инициализирован")
    
    def process_image(self, image_path: Path) -> RawOCRResult:
        """
        Обрабатывает изображение через полный пайплайн extraction.
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            RawOCRResult: Контракт D1->D2 с full_text и words[]
        """
        try:
            logger.info(f"[Extraction] Обработка: {image_path.name}")
            
            # 1. Preprocessing (если есть препроцессор)
            preprocessing_applied: List[str] = []
            
            if self.image_preprocessor:
                logger.debug("[Extraction] Этап 1: Preprocessing")
                processed_image, preprocess_metadata = self._preprocess_image(image_path)
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
                        preprocessing_applied=preprocessing_applied
                    )
                )
            
            logger.info(
                f"[Extraction] Готово: {image_path.name} "
                f"({len(result.words)} слов, {len(result.full_text)} символов)"
            )
            
            return result
            
        except ExtractionError:
            raise
        except Exception as e:
            logger.error(f"[Extraction] Ошибка: {e}")
            raise ExtractionError(
                message=f"Ошибка при обработке: {image_path}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def _preprocess_image(self, image_path: Path) -> tuple[bytes, dict]:
        """Выполняет preprocessing изображения."""
        try:
            if not self.image_preprocessor:
                raise ImageProcessingError(
                    message="Препроцессор не указан",
                    component="ExtractionPipeline"
                )
            
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
    
    def batch_process(self, image_paths: List[Path]) -> dict:
        """
        Обрабатывает несколько изображений.
        
        Args:
            image_paths: Список путей к изображениям
            
        Returns:
            dict: Статистика обработки
        """
        results = {
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
