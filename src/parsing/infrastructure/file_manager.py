"""
Менеджер файлов для домена Parsing.

Реализует файловые операции специфичные для домена Parsing.
"""

import json
from pathlib import Path
from typing import Dict, Any
import shutil
from loguru import logger

from ..domain.exceptions import ParsingFileNotFoundError, ParsingFileWriteError


class ParsingFileManager:
    """Менеджер файлов для домена Parsing."""
    
    def save_json(self, data: Dict[str, Any], file_path: Path) -> Path:
        """
        Сохраняет данные в JSON файл.
        
        Args:
            data: Данные для сохранения
            file_path: Путь для сохранения
            
        Returns:
            Путь к сохраненному файлу
            
        Raises:
            ParsingFileWriteError: Если не удалось сохранить файл
        """
        try:
            # Создаем директорию если не существует
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"[Parsing] Файл сохранен: {file_path}")
            return file_path
            
        except (IOError, OSError, TypeError) as e:
            raise ParsingFileWriteError(
                message=f"Не удалось сохранить JSON файл: {file_path}",
                component="ParsingFileManager",
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
            ParsingFileNotFoundError: Если файл не существует
            ParsingFileWriteError: Если не удалось загрузить файл
        """
        try:
            if not file_path.exists():
                raise ParsingFileNotFoundError(
                    message=f"Файл не найден: {file_path}",
                    component="ParsingFileManager"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"[Parsing] Файл загружен: {file_path}")
            return data
            
        except ParsingFileNotFoundError:
            raise
        except (IOError, OSError, json.JSONDecodeError) as e:
            raise ParsingFileWriteError(
                message=f"Не удалось загрузить JSON файл: {file_path}",
                component="ParsingFileManager",
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
            ParsingFileWriteError: Если не удалось создать директорию
        """
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"[Parsing] Директория создана/проверена: {directory_path}")
            return directory_path
            
        except (IOError, OSError) as e:
            raise ParsingFileWriteError(
                message=f"Не удалось создать директорию: {directory_path}",
                component="ParsingFileManager",
                original_error=e
            )
    
    def save_parsing_result(self, result_data: Dict[str, Any], source_file: str, output_dir: Path) -> Dict[str, Path]:
        """
        Сохраняет результат parsing в стандартном формате.
        
        Args:
            result_data: Структурированные данные чека
            source_file: Имя исходного файла (без расширения)
            output_dir: Директория для сохранения
            
        Returns:
            Словарь с путями к сохраненным файлам
        """
        try:
            # Создаем поддиректории
            post_ocr_dir = output_dir / "post_ocr"
            final_dir = post_ocr_dir / "final"
            
            self.ensure_directory(final_dir)
            
            # Сохраняем основной результат
            json_path = final_dir / f"{source_file}_result.json"
            self.save_json(result_data, json_path)
            
            # Сохраняем текстовую версию
            txt_path = final_dir / f"{source_file}_result.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(result_data.get('full_text', ''))
            
            logger.debug(f"[Parsing] Результаты сохранены: {json_path}")
            
            return {
                "json": json_path,
                "txt": txt_path
            }
            
        except Exception as e:
            raise ParsingFileWriteError(
                message=f"Не удалось сохранить результат parsing: {source_file}",
                component="ParsingFileManager",
                original_error=e
            )
    
    def get_ocr_files(self, directory_path: Path) -> list[Path]:
        """
        Получает список файлов с OCR данными в директории.
        
        Args:
            directory_path: Путь к директории
            
        Returns:
            Список путей к файлам OCR данных (.json)
        """
        try:
            if not directory_path.exists():
                return []
            
            # Ищем JSON файлы
            ocr_files = list(directory_path.glob('*.json'))
            
            return sorted(ocr_files)
            
        except Exception as e:
            logger.warning(f"[Parsing] Ошибка при получении файлов OCR: {e}")
            return []
