"""
Менеджер файлов для домена Extraction.

Реализует файловые операции специфичные для домена Extraction.
"""

import json
from pathlib import Path
from typing import Dict, Any
import shutil
from loguru import logger

from ..domain.exceptions import ExtractionFileNotFoundError, ExtractionFileWriteError


class ExtractionFileManager:
    """Менеджер файлов для домена Extraction."""
    
    def save_json(self, data: Dict[str, Any], file_path: Path) -> Path:
        """
        Сохраняет данные в JSON файл.
        
        Args:
            data: Данные для сохранения
            file_path: Путь для сохранения
            
        Returns:
            Путь к сохраненному файлу
            
        Raises:
            ExtractionFileWriteError: Если не удалось сохранить файл
        """
        try:
            # Создаем директорию если не существует
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"[Extraction] Файл сохранен: {file_path}")
            return file_path
            
        except (IOError, OSError, TypeError) as e:
            raise ExtractionFileWriteError(
                message=f"Не удалось сохранить JSON файл: {file_path}",
                component="ExtractionFileManager",
                original_error=e
            )
    
    def load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        Загружает данные из JSON файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Загруженные данные
            
        Raises:
            ExtractionFileNotFoundError: Если файл не существует
            ExtractionFileWriteError: Если не удалось загрузить файл
        """
        try:
            if not file_path.exists():
                raise ExtractionFileNotFoundError(
                    message=f"Файл не найден: {file_path}",
                    component="ExtractionFileManager"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"[Extraction] Файл загружен: {file_path}")
            return data
            
        except ExtractionFileNotFoundError:
            raise
        except (IOError, OSError, json.JSONDecodeError) as e:
            raise ExtractionFileWriteError(
                message=f"Не удалось загрузить JSON файл: {file_path}",
                component="ExtractionFileManager",
                original_error=e
            )
    
    def ensure_directory(self, directory_path: Path) -> Path:
        """
        Создает директорию если она не существует.
        
        Args:
            directory_path: Путь к директории
            
        Returns:
            Путь к созданной/существующей директории
            
        Raises:
            ExtractionFileWriteError: Если не удалось создать директорию
        """
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"[Extraction] Директория создана/проверена: {directory_path}")
            return directory_path
            
        except (IOError, OSError) as e:
            raise ExtractionFileWriteError(
                message=f"Не удалось создать директорию: {directory_path}",
                component="ExtractionFileManager",
                original_error=e
            )
    
    def save_raw_ocr(self, ocr_data: Dict[str, Any], filename: str, output_dir: Path) -> Path:
        """
        Сохраняет raw_ocr результат в стандартном формате.
        
        Args:
            ocr_data: Данные OCR
            filename: Имя файла (без расширения)
            output_dir: Директория для сохранения
            
        Returns:
            Путь к сохраненному файлу
        """
        try:
            # Создаем директорию если не существует
            self.ensure_directory(output_dir)
            
            # Формируем полный путь
            file_path = output_dir / f"{filename}.json"
            
            # Сохраняем данные
            return self.save_json(ocr_data, file_path)
            
        except Exception as e:
            raise ExtractionFileWriteError(
                message=f"Не удалось сохранить raw_ocr: {filename}",
                component="ExtractionFileManager",
                original_error=e
            )
    
    def get_image_files(self, directory_path: Path) -> list[Path]:
        """
        Получает список файлов изображений в директории.
        
        Args:
            directory_path: Путь к директории
            
        Returns:
            Список путей к файлам изображений
        """
        try:
            if not directory_path.exists():
                return []
            
            # Поддерживаемые форматы
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']
            
            image_files = []
            for ext in image_extensions:
                image_files.extend(directory_path.glob(f'*{ext}'))
                image_files.extend(directory_path.glob(f'*{ext.upper()}'))
            
            return sorted(image_files)
            
        except Exception as e:
            logger.warning(f"[Extraction] Ошибка при получении файлов изображений: {e}")
            return []
