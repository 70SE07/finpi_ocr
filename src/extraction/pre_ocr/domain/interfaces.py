"""
Pre-OCR Domain: Интерфейсы и абстракции.

Определяет контракты для всех компонентов preprocessing pipeline.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
import numpy.typing as npt

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
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение через весь pipeline.
        
        Args:
            image_path: Путь к файлу изображения
            context: Dict с контекстом для Stage 3 Selector (опционально):
              - strategy: Dict с retry стратегией для Feedback Loop
                        {"name": "adaptive"|"aggressive"|"minimal"}
            
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
    def compress(self, image: npt.NDArray[np.uint8], original_bytes: int) -> Any:
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
        target_size: Optional[Tuple[int, int]] = None
    ) -> npt.NDArray[np.uint8]:
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
    def analyze(self, image: npt.NDArray[np.uint8]) -> Any:
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
        context: Optional[Dict[str, Any]] = None
    ) -> list[str]:
        """
        Выбирает план обработки на основе метрик (DEPRECATED).
        
        DEPRECATED: Используйте select_filters() вместо этого метода.
        Этот метод оставлен для обратной совместимости.
        
        Args:
            metrics: Dict с метриками изображения
            context: Dict с контекстом (не используется)
        """
        pass


class IExecutorStage(IPreprocessingStage):
    """Stage 4: Executor (применение фильтров)."""
    
    @abstractmethod
    def execute(
        self, 
        image: npt.NDArray[np.uint8],
        filter_plan: Any  # FilterPlan или List[str]
    ) -> npt.NDArray[np.uint8]:
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
    def encode(
        self, 
        image: npt.NDArray[np.uint8], 
        quality: Optional[int] = None, 
        image_size: Optional[Tuple[int, int]] = None
    ) -> bytes:
        """Кодирует изображение в JPEG bytes."""
        pass
