"""
Интерфейсы (абстрактные классы) для домена Extraction.

Домен Extraction отвечает за:
1. Preprocessing изображений (pre-ocr)
2. OCR распознавание текста
3. Возврат RawOCRResult (контракт D1->D2)

ВАЖНО: Все методы возвращают типы из contracts/d1_extraction_dto.py
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from contracts.d1_extraction_dto import RawOCRResult


class IOCRProvider(ABC):
    """
    Интерфейс для провайдеров OCR (домен Extraction).
    
    Возвращает RawOCRResult — контракт D1->D2.
    """
    
    @abstractmethod
    def recognize(self, image_content: bytes, source_file: str = "unknown") -> RawOCRResult:
        """
        Распознаёт текст на изображении.
        
        Args:
            image_content: Байты изображения
            source_file: Имя исходного файла (для метаданных)
            
        Returns:
            RawOCRResult: Контракт D1->D2 с full_text и words[]
        """
        pass
    
    @abstractmethod
    def recognize_from_file(self, image_path: Path) -> RawOCRResult:
        """
        Распознаёт текст из файла изображения.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            RawOCRResult: Контракт D1->D2
        """
        pass


class IImagePreprocessor(ABC):
    """Интерфейс для препроцессоров изображений (домен Extraction)."""
    
    @abstractmethod
    def process(
        self, 
        image_path: Path, 
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение перед OCR.
        
        Args:
            image_path: Путь к файлу изображения
            context: Dict с контекстом для Stage 3 Selector (опционально)
            
        Returns:
            Кортеж: (обработанные байты, метаданные обработки)
        """
        pass


class IExtractionPipeline(ABC):
    """
    Интерфейс для пайплайна extraction (домен Extraction).
    
    ЦКП: RawOCRResult — 100% качественный OCR результат.
    """
    
    @abstractmethod
    def process_image(self, image_path: Path) -> RawOCRResult:
        """
        Обрабатывает изображение через полный пайплайн extraction.
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            RawOCRResult: Контракт D1->D2
        """
        pass
