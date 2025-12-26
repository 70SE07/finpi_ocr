"""
Пайплайн для домена Parsing.

Обрабатывает сырые данные OCR через:
1. Парсинг чеков
2. Сохранение структурированных результатов
"""

from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from ..domain.interfaces import IParsingPipeline, IReceiptParser
from ..domain.exceptions import ParsingError, ParsingFileNotFoundError
from ..infrastructure.file_manager import ParsingFileManager


class ParsingPipeline(IParsingPipeline):
    """
    Пайплайн домена Parsing.
    
    Координирует:
    1. Парсинг сырых данных OCR
    2. Сохранение структурированных результатов
    """
    
    def __init__(
        self,
        receipt_parser: IReceiptParser,
        file_manager: Optional[ParsingFileManager] = None,
        output_dir: Optional[Path] = None,
        save_intermediate: bool = False
    ):
        """
        Инициализация пайплайна parsing.
        
        Args:
            receipt_parser: Парсер чеков
            file_manager: Менеджер файлов (опционально)
            output_dir: Директория для сохранения структурированных результатов
            save_intermediate: Сохранять ли промежуточные результаты
        """
        self.receipt_parser = receipt_parser
        self.file_manager = file_manager or ParsingFileManager()
        self.output_dir = output_dir
        self.save_intermediate = save_intermediate
        
        logger.info("[Parsing] ParsingPipeline инициализирован")
    
    def process_ocr_data(self, ocr_data: Dict[str, Any], source_file: str = "") -> Dict[str, Any]:
        """
        Обрабатывает сырые данные OCR через полный пайплайн parsing.
        
        Args:
            ocr_data: Сырые данные OCR (формат raw_ocr)
            source_file: Имя исходного файла
            
        Returns:
            Структурированные данные чека
        """
        try:
            logger.info(f"[Parsing] Начало обработки OCR данных: {source_file}")
            
            # 1. Парсинг данных
            logger.debug("[Parsing] Этап 1: Парсинг данных")
            parsing_result = self._parse_ocr_data(ocr_data, source_file)
            
            # 2. Сохранение результатов (если нужно)
            if self.output_dir and source_file:
                logger.debug("[Parsing] Этап 2: Сохранение результатов")
                self._save_parsing_result(parsing_result, source_file)
            
            logger.info(f"[Parsing] Обработка завершена успешно: {source_file}")
            return parsing_result
            
        except ParsingError as e:
            logger.error(f"[Parsing] Ошибка в пайплайне parsing: {e}")
            raise
        except Exception as e:
            logger.error(f"[Parsing] Неожиданная ошибка: {e}")
            raise ParsingError(
                message=f"Неожиданная ошибка при обработке OCR данных: {source_file}",
                component="ParsingPipeline",
                original_error=e
            )
    
    def process_ocr_file(self, ocr_file_path: Path, save_output: bool = True) -> Dict[str, Any]:
        """
        Обрабатывает файл с OCR данными через полный пайплайн parsing.
        
        Args:
            ocr_file_path: Путь к файлу с OCR данными (raw_ocr.json)
            save_output: Сохранять ли структурированный результат
            
        Returns:
            Структурированные данные чека
        """
        try:
            logger.info(f"[Parsing] Обработка OCR файла: {ocr_file_path}")
            
            # Проверяем существование файла
            if not ocr_file_path.exists():
                raise ParsingFileNotFoundError(
                    message=f"OCR файл не найден: {ocr_file_path}",
                    component="ParsingPipeline"
                )
            
            # Загружаем данные
            ocr_data = self.file_manager.load_json(ocr_file_path)
            
            # Извлекаем source_file из metadata или имени файла
            source_file = ocr_data.get("metadata", {}).get("source_file", ocr_file_path.stem)
            
            # Обрабатываем данные
            parsing_result = self.process_ocr_data(ocr_data, source_file)
            
            # Сохраняем результат если нужно
            if save_output and self.output_dir:
                self._save_parsing_result(parsing_result, source_file)
            
            return parsing_result
            
        except ParsingFileNotFoundError:
            raise
        except Exception as e:
            raise ParsingError(
                message=f"Ошибка при обработке OCR файла: {ocr_file_path}",
                component="ParsingPipeline",
                original_error=e
            )
    
    def _parse_ocr_data(self, ocr_data: Dict[str, Any], source_file: str) -> Dict[str, Any]:
        """Парсит данные OCR."""
        try:
            return self.receipt_parser.parse(ocr_data, source_file)
            
        except Exception as e:
            raise ParsingError(
                message=f"Ошибка парсинга OCR данных: {source_file}",
                component="ParsingPipeline",
                original_error=e
            )
    
    def _save_parsing_result(self, result_data: Dict[str, Any], source_file: str) -> None:
        """Сохраняет результат parsing."""
        try:
            if not self.output_dir:
                logger.warning("[Parsing] Директория для сохранения не указана, сохранение пропущено")
                return
            
            # Создаем поддиректорию для исходного файла
            output_subdir = self.output_dir / source_file
            self.file_manager.ensure_directory(output_subdir)
            
            # Сохраняем результат
            self.file_manager.save_parsing_result(result_data, source_file, output_subdir)
            logger.info(f"[Parsing] Результат parsing сохранен в: {output_subdir}")
            
        except Exception as e:
            logger.warning(f"[Parsing] Не удалось сохранить результат parsing: {e}")
            # Не прерываем выполнение из-за ошибки сохранения
    
    def batch_process(self, input_dir: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Обрабатывает все OCR файлы в директории.
        
        Args:
            input_dir: Директория с OCR файлами (raw_ocr.json)
            output_dir: Директория для сохранения результатов (опционально)
            
        Returns:
            Статистика обработки
        """
        try:
            logger.info(f"[Parsing] Пакетная обработка OCR файлов из: {input_dir}")
            
            # Получаем список OCR файлов
            ocr_files = self.file_manager.get_ocr_files(input_dir)
            
            if not ocr_files:
                logger.warning(f"[Parsing] В директории нет OCR файлов: {input_dir}")
                return {"processed": 0, "success": 0, "failed": 0}
            
            logger.info(f"[Parsing] Найдено OCR файлов: {len(ocr_files)}")
            
            # Используем указанную output_dir или дефолтную
            target_output_dir = output_dir or self.output_dir
            
            # Обрабатываем каждый файл
            results = {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "files": []
            }
            
            for ocr_file in ocr_files:
                try:
                    logger.debug(f"[Parsing] Обработка: {ocr_file.name}")
                    
                    # Обрабатываем OCR файл
                    parsing_result = self.process_ocr_file(ocr_file, save_output=True)
                    
                    results["success"] += 1
                    results["files"].append({
                        "file": ocr_file.name,
                        "status": "success",
                        "source_file": parsing_result.get("source_file", "unknown")
                    })
                    
                except Exception as e:
                    logger.error(f"[Parsing] Ошибка при обработке {ocr_file.name}: {e}")
                    results["failed"] += 1
                    results["files"].append({
                        "file": ocr_file.name,
                        "status": "failed",
                        "error": str(e)
                    })
                
                results["processed"] += 1
            
            logger.info(f"[Parsing] Пакетная обработка завершена: {results['success']} успешно, {results['failed']} с ошибками")
            return results
            
        except Exception as e:
            raise ParsingError(
                message=f"Ошибка при пакетной обработке: {input_dir}",
                component="ParsingPipeline",
                original_error=e
            )
