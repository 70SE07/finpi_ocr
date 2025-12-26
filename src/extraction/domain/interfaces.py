"""
Интерфейсы (абстрактные классы) для домена Extraction.

Домен Extraction отвечает за:
1. Preprocessing изображений (pre-ocr)
2. OCR распознавание текста
3. Сохранение сырых результатов в raw_ocr.json
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple


class IOCRProvider(ABC):
    """Интерфейс для провайдеров OCR (домен Extraction)."""
    
    @abstractmethod
    def recognize(self, image_content: bytes) -> Dict[str, Any]:
        """
        Распознаёт текст на изображении.
        
        Args:
            image_content: Байты изображения
            
        Returns:
            Словарь с результатами OCR в формате raw_ocr
        """
        pass
    
    @abstractmethod
    def recognize_from_file(self, image_path: Path) -> Dict[str, Any]:
        """
        Распознаёт текст из файла изображения.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Словарь с результатами OCR в формате raw_ocr
        """
        pass


class IImagePreprocessor(ABC):
    """Интерфейс для препроцессоров изображений (домен Extraction)."""
    
    @abstractmethod
    def process(self, image_path: Path) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение перед OCR.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Кортеж: (обработанные байты, метаданные обработки)
        """
        pass


class IExtractionPipeline(ABC):
    """Интерфейс для пайплайна extraction (домен Extraction)."""
    
    @abstractmethod
    def process_image(self, image_path: Path, save_output: bool = True) -> Dict[str, Any]:
        """
        Обрабатывает изображение через полный пайплайн extraction.
        
        Args:
            image_path: Путь к изображению
            save_output: Сохранять ли raw_ocr результат
            
        Returns:
            Словарь с результатами extraction (raw_ocr формат)
        """
        pass
    
    @abstractmethod
    def process_image_to_file(self, image_path: Path, output_path: Path) -> Path:
        """
        Обрабатывает изображение и сохраняет результат в файл.
        
        Args:
            image_path: Путь к изображению
            output_path: Путь для сохранения raw_ocr.json
            
        Returns:
            Путь к сохраненному файлу
        """
        pass
