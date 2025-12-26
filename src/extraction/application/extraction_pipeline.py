"""
Пайплайн для домена Extraction.

Обрабатывает изображения через:
1. Preprocessing изображений
2. OCR распознавание текста
3. Сохранение сырых результатов в raw_ocr.json
"""

from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from ..domain.interfaces import IExtractionPipeline, IOCRProvider, IImagePreprocessor
from ..domain.exceptions import ExtractionError, ImageProcessingError, OCRProcessingError
from ..infrastructure.file_manager import ExtractionFileManager


class ExtractionPipeline(IExtractionPipeline):
    """
    Пайплайн домена Extraction.
    
    Координирует:
    1. Preprocessing изображения
    2. OCR распознавание
    3. Сохранение raw_ocr результатов
    """
    
    def __init__(
        self,
        ocr_provider: IOCRProvider,
        image_preprocessor: Optional[IImagePreprocessor] = None,
        file_manager: Optional[ExtractionFileManager] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Инициализация пайплайна extraction.
        
        Args:
            ocr_provider: Провайдер OCR
            image_preprocessor: Препроцессор изображений (опционально)
            file_manager: Менеджер файлов (опционально)
            output_dir: Директория для сохранения raw_ocr результатов
        """
        self.ocr_provider = ocr_provider
        self.image_preprocessor = image_preprocessor
        self.file_manager = file_manager or ExtractionFileManager()
        self.output_dir = output_dir
        
        logger.info("[Extraction] ExtractionPipeline инициализирован")
    
    def process_image(self, image_path: Path, save_output: bool = True) -> Dict[str, Any]:
        """
        Обрабатывает изображение через полный пайплайн extraction.
        
        Args:
            image_path: Путь к изображению
            save_output: Сохранять ли raw_ocr результат
            
        Returns:
            Словарь с результатами extraction (raw_ocr формат)
        """
        try:
            logger.info(f"[Extraction] Начало обработки изображения: {image_path}")
            
            # 1. Preprocessing (если есть препроцессор)
            processed_image = None
            preprocess_metadata = {}
            
            if self.image_preprocessor:
                logger.debug("[Extraction] Этап 1: Preprocessing изображения")
                processed_image, preprocess_metadata = self._preprocess_image(image_path)
            else:
                logger.debug("[Extraction] Этап 1: Preprocessing пропущен (препроцессор не указан)")
                # Читаем исходное изображение
                with open(image_path, 'rb') as f:
                    processed_image = f.read()
            
            # 2. OCR распознавание
            logger.debug("[Extraction] Этап 2: OCR распознавание")
            ocr_result = self._perform_ocr(processed_image, str(image_path))
            
            # 3. Сохранение результатов (если нужно)
            if save_output and self.output_dir:
                logger.debug("[Extraction] Этап 3: Сохранение результатов")
                self._save_raw_ocr(ocr_result, image_path)
            
            # Добавляем метаданные preprocessing в результат
            if preprocess_metadata:
                ocr_result.setdefault('metadata', {})
                ocr_result['metadata']['preprocessing'] = preprocess_metadata
            
            logger.info(f"[Extraction] Обработка завершена успешно: {image_path}")
            return ocr_result
            
        except ExtractionError as e:
            logger.error(f"[Extraction] Ошибка в пайплайне extraction: {e}")
            raise
        except Exception as e:
            logger.error(f"[Extraction] Неожиданная ошибка: {e}")
            raise ExtractionError(
                message=f"Неожиданная ошибка при обработке изображения: {image_path}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def process_image_to_file(self, image_path: Path, output_path: Path) -> Path:
        """
        Обрабатывает изображение и сохраняет результат в файл.
        
        Args:
            image_path: Путь к изображению
            output_path: Путь для сохранения raw_ocr.json
            
        Returns:
            Путь к сохраненному файлу
        """
        try:
            logger.info(f"[Extraction] Обработка изображения с сохранением в файл: {image_path} -> {output_path}")
            
            # Обрабатываем изображение
            ocr_result = self.process_image(image_path, save_output=False)
            
            # Сохраняем результат в указанный файл
            self.file_manager.save_json(ocr_result, output_path)
            
            logger.info(f"[Extraction] Результат сохранен: {output_path}")
            return output_path
            
        except Exception as e:
            raise ExtractionError(
                message=f"Ошибка при обработке изображения с сохранением в файл: {image_path}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def _preprocess_image(self, image_path: Path) -> tuple[bytes, Dict[str, Any]]:
        """Выполняет preprocessing изображения."""
        try:
            if not self.image_preprocessor:
                raise ImageProcessingError(
                    message="Препроцессор изображений не указан",
                    component="ExtractionPipeline"
                )
            
            return self.image_preprocessor.process(image_path)
            
        except Exception as e:
            raise ImageProcessingError(
                message=f"Ошибка preprocessing изображения: {image_path}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def _perform_ocr(self, image_content: bytes, source_info: str) -> Dict[str, Any]:
        """Выполняет OCR распознавание."""
        try:
            return self.ocr_provider.recognize(image_content)
            
        except Exception as e:
            raise OCRProcessingError(
                message=f"Ошибка OCR распознавания: {source_info}",
                component="ExtractionPipeline",
                original_error=e
            )
    
    def _save_raw_ocr(self, ocr_data: Dict[str, Any], image_path: Path) -> None:
        """Сохраняет raw_ocr результат."""
        try:
            if not self.output_dir:
                logger.warning("[Extraction] Директория для сохранения не указана, сохранение пропущено")
                return
            
            # Создаем директорию если не существует
            self.file_manager.ensure_directory(self.output_dir)
            
            # Сохраняем raw_ocr результат
            filename = image_path.stem
            output_file = self.output_dir / f"{filename}.json"
            
            self.file_manager.save_json(ocr_data, output_file)
            logger.info(f"[Extraction] Raw_ocr сохранен: {output_file}")
            
        except Exception as e:
            logger.warning(f"[Extraction] Не удалось сохранить raw_ocr: {e}")
            # Не прерываем выполнение из-за ошибки сохранения
    
    def batch_process(self, input_dir: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Обрабатывает все изображения в директории.
        
        Args:
            input_dir: Директория с изображениями
            output_dir: Директория для сохранения результатов (опционально)
            
        Returns:
            Статистика обработки
        """
        try:
            logger.info(f"[Extraction] Пакетная обработка изображений из: {input_dir}")
            
            # Получаем список изображений
            image_files = self.file_manager.get_image_files(input_dir)
            
            if not image_files:
                logger.warning(f"[Extraction] В директории нет изображений: {input_dir}")
                return {"processed": 0, "success": 0, "failed": 0}
            
            logger.info(f"[Extraction] Найдено изображений: {len(image_files)}")
            
            # Используем указанную output_dir или дефолтную
            target_output_dir = output_dir or self.output_dir
            
            # Обрабатываем каждое изображение
            results = {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "files": []
            }
            
            for image_file in image_files:
                try:
                    logger.debug(f"[Extraction] Обработка: {image_file.name}")
                    
                    # Обрабатываем изображение
                    ocr_result = self.process_image(image_file, save_output=True)
                    
                    results["success"] += 1
                    results["files"].append({
                        "file": image_file.name,
                        "status": "success",
                        "result": f"{image_file.stem}.json"
                    })
                    
                except Exception as e:
                    logger.error(f"[Extraction] Ошибка при обработке {image_file.name}: {e}")
                    results["failed"] += 1
                    results["files"].append({
                        "file": image_file.name,
                        "status": "failed",
                        "error": str(e)
                    })
                
                results["processed"] += 1
            
            logger.info(f"[Extraction] Пакетная обработка завершена: {results['success']} успешно, {results['failed']} с ошибками")
            return results
            
        except Exception as e:
            raise ExtractionError(
                message=f"Ошибка при пакетной обработке: {input_dir}",
                component="ExtractionPipeline",
                original_error=e
            )
