"""
Pre-OCR Domain: Интерфейсы и абстракции.

Определяет контракты для всех компонентов preprocessing pipeline.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np

# Импортируем контракты для типизации
from src.domain.contracts import ImageMetrics, FilterPlan, FilterType, ExecutorResponse


class IImagePreprocessor(ABC):
    """
    Интерфейс препроцессора изображений (D1 домен).
    
    Отвечает за полный цикл preprocessing:
    Путь к файлу → Обработанное изображение (bytes)
    """
    
    @abstractmethod
    def process(
        self, 
        image_path: Path, 
        context: Optional[Dict] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение через весь pipeline.
        
        Args:
            image_path: Путь к файлу изображения
            context: Dict с контекстом для Stage 3 Selector (опционально):
              - shop: str - название магазина (Rewe, Aldi, DM, Edeka, ...)
              - material: str - материал чека (paper, thermal, ...)
              - lighting: str - качество освещения (good, poor, ...)
              - device: str - модель устройства (iphone_12, pixel, ...)
            
        Returns:
            (image_bytes, metadata) где:
            - image_bytes: JPEG bytes для Google Vision API
            - metadata: Dict с ключом 'applied' (список применённых фильтров)
        """
        pass


class IPreprocessingStage(ABC):
    """Интерфейс для отдельного stage preprocessing."""
    pass


class IImageCompressionStage(IPreprocessingStage):
    """Stage 0: Compression (адаптивное сжатие)."""
    
    @abstractmethod
    def compute_target_size(
        self, 
        width: int, 
        height: int, 
        file_size_bytes: int
    ) -> tuple[int, int]:
        """
        Вычисляет целевой размер для сжатия БЕЗ загрузки изображения.
        
        Args:
            width: исходная ширина
            height: исходная высота
            file_size_bytes: размер файла в байтах
            
        Returns:
            (target_width, target_height)
        """
        pass
    
    @abstractmethod
    def compress(self, image: np.ndarray, original_bytes: int) -> Any:
        """
        Сжимает изображение адаптивно.
        
        Возвращает CompressionResult из s0_compression.stage
        """
        pass


class IImagePreparationStage(IPreprocessingStage):
    """Stage 1: Preparation (загрузка + resize)."""
    
    @abstractmethod
    def process(
        self, 
        image_path: Path, 
        target_size: Optional[tuple] = None
    ) -> np.ndarray:
        """
        Загружает и нормализует размер изображения.
        
        Args:
            image_path: Path к файлу изображения
            target_size: (width, height) - опциональный целевой размер
        """
        pass


class IAnalyzerStage(IPreprocessingStage):
    """Stage 2: Analyzer (анализ метрик)."""
    
    @abstractmethod
    def analyze(self, image: np.ndarray):
        """
        Анализирует метрики изображения.
        
        Возвращает ImageMetrics (типизированный контракт) с валидацией.
        """
        pass


class ISelectorStage(IPreprocessingStage):
    """Stage 3: Selector (выбор стратегии)."""
    
    @abstractmethod
    def select_plan(
        self, 
        metrics: Dict[str, float], 
        context: Optional[Dict] = None
    ) -> list:
        """
        Выбирает план обработки на основе метрик и контекста.
        
        Args:
            metrics: Dict с метриками изображения
            context: Dict с контекстом (shop, material, lighting, device)
        """
        pass


class IExecutorStage(IPreprocessingStage):
    """Stage 4: Executor (применение фильтров)."""
    
    @abstractmethod
    def execute(
        self, 
        image: np.ndarray,
        filter_plan: Any  # FilterPlan или List[str]
    ) -> np.ndarray:
        """
        Применяет фильтры согласно плану.
        
        Args:
            image: np.ndarray (BGR или Grayscale)
            filter_plan: FilterPlan (типизированный) или List[str] для совместимости
            
        Returns:
            np.ndarray (Grayscale, обработанное)
        """
        pass


class IEncoderStage(IPreprocessingStage):
    """Stage 5: Encoder (кодирование в JPEG)."""
    
    @abstractmethod
    def encode(self, image: np.ndarray, quality: int = None, image_size: tuple = None) -> bytes:
        """Кодирует изображение в JPEG bytes."""
        pass
