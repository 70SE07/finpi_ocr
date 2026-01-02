"""
Pre-OCR Pipeline для домена Extraction.

Оркестратор операций предобработки изображений.
По ADR-013: Pipeline = оркестратор операций, сам НЕ выполняет обработку,
только вызывает операции в нужном порядке.

Пайплайн:
1. Чтение файла (ImageFileReader)
2. Сжатие (ImageCompressor)
3. Конвертация в Grayscale / Blue Channel (GrayscaleConverter)
4. Кодирование в bytes (ImageEncoder)
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from loguru import logger

from ..domain.interfaces import IImagePreprocessor
from .elements.image_compressor import ImageCompressor
from .elements.grayscale import GrayscaleConverter
from .image_file_reader import ImageFileReader
from .image_encoder import ImageEncoder


class PreOCRPipeline(IImagePreprocessor):
    """
    Оркестратор предобработки изображений для OCR.
    
    По ADR-013: Pipeline = оркестратор операций.
    Сам НЕ выполняет обработку, только вызывает операции в нужном порядке.
    
    Пайплайн операций:
    1. ImageFileReader: чтение и декодирование файла
    2. ImageCompressor: сжатие изображения
    3. GrayscaleConverter: конвертация в Grayscale / Blue Channel
    4. ImageEncoder: кодирование в JPEG bytes
    """

    def __init__(
        self, 
        compressor: Optional[ImageCompressor] = None, 
        grayscale: Optional[GrayscaleConverter] = None,
        file_reader: Optional[ImageFileReader] = None,
        encoder: Optional[ImageEncoder] = None
    ):
        """
        Инициализация пайплайна.
        
        Args:
            compressor: Компрессор изображений (опционально)
            grayscale: Конвертер в grayscale (опционально)
            file_reader: Читатель файлов (опционально)
            encoder: Энкодер изображений (опционально)
        """
        self.compressor = compressor or ImageCompressor(mode="adaptive")
        self.grayscale = grayscale or GrayscaleConverter()
        self.file_reader = file_reader or ImageFileReader()
        self.encoder = encoder or ImageEncoder()
        
        logger.debug(
            f"[PreOCRPipeline] Инициализирован "
            f"(DI: c={compressor is not None}, g={grayscale is not None}, "
            f"fr={file_reader is not None}, enc={encoder is not None})"
        )

    def process(self, image_path: Path) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение через пайплайн операций.
        
        Оркестрация:
        1. Читаем файл (ImageFileReader)
        2. Сжимаем (ImageCompressor)
        3. Конвертируем в Grayscale (GrayscaleConverter)
        4. Кодируем в bytes (ImageEncoder)
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Кортеж: (processed_bytes, metadata)
        """
        # 1. Читаем и декодируем файл
        image, raw_bytes = self.file_reader.read(image_path)
        
        # 2. Сжимаем изображение
        comp_result = self.compressor.compress(image, original_bytes=len(raw_bytes))
        
        # 3. Конвертируем в Grayscale / Blue Channel
        logger.debug("[PreOCRPipeline] Запуск Grayscale/BlueChannel conversion")
        gray_result = self.grayscale.process(comp_result.image)
        
        # 4. Кодируем результат в байты для отправки в Google Vision
        # Используем JPEG с тем же качеством, что и при сжатии
        processed_bytes = self.encoder.encode(gray_result.image, quality=comp_result.quality)
        
        # 5. Формируем метаданные
        metadata = {
            "original_size": comp_result.original_size,
            "processed_size": gray_result.original_size,  # Это размер ПОСЛЕ сжатия (w, h)
            "compressed_size_kb": len(processed_bytes) / 1024,
            "scale_factor": comp_result.scale_factor,
            "quality": comp_result.quality,
            "grayscale_converted": gray_result.was_converted
        }
        
        return processed_bytes, metadata
