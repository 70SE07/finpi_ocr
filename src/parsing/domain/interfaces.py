"""
Интерфейсы (абстрактные классы) для домена Parsing.

Домен Parsing отвечает за:
1. Обработку layout сырых данных OCR
2. Определение локали
3. Извлечение метаданных
4. Семантическое извлечение товаров
5. Сохранение структурированных результатов
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List


class IReceiptParser(ABC):
    """Интерфейс для парсеров чеков (домен Parsing)."""
    
    @abstractmethod
    def parse(self, ocr_data: Dict[str, Any], source_file: str = "") -> Dict[str, Any]:
        """
        Парсит сырые данные OCR в структурированный формат.
        
        Args:
            ocr_data: Сырые данные OCR (формат raw_ocr)
            source_file: Имя исходного файла
            
        Returns:
            Структурированные данные чека
        """
        pass
    
    @abstractmethod
    def parse_from_file(self, ocr_file_path: Path) -> Dict[str, Any]:
        """
        Парсит данные OCR из файла.
        
        Args:
            ocr_file_path: Путь к файлу с OCR данными (raw_ocr.json)
            
        Returns:
            Структурированные данные чека
        """
        pass


class ILayoutProcessor(ABC):
    """Интерфейс для обработки layout (структуры) чека (домен Parsing)."""
    
    @abstractmethod
    def process(self, ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Обрабатывает layout чека.
        
        Args:
            ocr_data: Сырые данные OCR
            
        Returns:
            Список строк чека с метаданными
        """
        pass


class ILocaleDetector(ABC):
    """Интерфейс для детектора локали (домен Parsing)."""
    
    @abstractmethod
    def detect(self, texts: List[str]) -> str:
        """
        Определяет локаль чека.
        
        Args:
            texts: Список текстовых строк чека
            
        Returns:
            Код локали (например, 'de_DE', 'pl_PL')
        """
        pass


class IMetadataExtractor(ABC):
    """Интерфейс для извлечения метаданных (домен Parsing)."""
    
    @abstractmethod
    def extract(self, texts: List[str], locale_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает метаданные из чека.
        
        Args:
            texts: Список текстовых строк чека
            locale_config: Конфигурация локали
            
        Returns:
            Метаданные чека (магазин, дата, сумма и т.д.)
        """
        pass


class ISemanticExtractor(ABC):
    """Интерфейс для семантического извлечения товаров (домен Parsing)."""
    
    @abstractmethod
    def extract(self, lines: List[Dict[str, Any]], locale_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Извлекает товары из строк чека.
        
        Args:
            lines: Список строк чека
            locale_config: Конфигурация локали
            
        Returns:
            Список товаров с деталями
        """
        pass


class IParsingPipeline(ABC):
    """Интерфейс для пайплайна parsing (домен Parsing)."""
    
    @abstractmethod
    def process_ocr_data(self, ocr_data: Dict[str, Any], source_file: str = "") -> Dict[str, Any]:
        """
        Обрабатывает сырые данные OCR через полный пайплайн parsing.
        
        Args:
            ocr_data: Сырые данные OCR (формат raw_ocr)
            source_file: Имя исходного файла
            
        Returns:
            Структурированные данные чека
        """
        pass
    
    @abstractmethod
    def process_ocr_file(self, ocr_file_path: Path, save_output: bool = True) -> Dict[str, Any]:
        """
        Обрабатывает файл с OCR данными через полный пайплайн parsing.
        
        Args:
            ocr_file_path: Путь к файлу с OCR данными (raw_ocr.json)
            save_output: Сохранять ли структурированный результат
            
        Returns:
            Структурированные данные чека
        """
        pass
