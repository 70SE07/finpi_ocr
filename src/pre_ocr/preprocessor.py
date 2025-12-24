
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np
from loguru import logger

from .elements.image_compressor import ImageCompressor
from .elements.grayscale import GrayscaleConverter

class ImagePreprocessor:
    """
    Оркестратор предобработки изображений для OCR.
    
    Пайплайн:
    1. Сжатие (ImageCompressor)
    2. Конвертация в Grayscale / Blue Channel (GrayscaleConverter)
    """

    def __init__(
        self, 
        compressor: Optional[ImageCompressor] = None, 
        grayscale: Optional[GrayscaleConverter] = None
    ):
        self.compressor = compressor or ImageCompressor(adaptive=True)
        self.grayscale = grayscale or GrayscaleConverter()
        logger.debug(f"[Preprocessor] Иннициализирован (DI: c={compressor is not None}, g={grayscale is not None})")

    def process(self, image_path: Path) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение: читает -> сжимает -> конвертирует.
        
        Args:
            image_path: Путь к файлу
            
        Returns:
            (processed_bytes, metadata)
        """
        # 1. Читаем файл
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        with open(image_path, "rb") as f:
            raw_bytes = f.read()
            
        # 2. Сжимаем (если нужно)
        # compress_bytes возвращает (jpeg_bytes, result_obj)
        # Но нам удобнее работать с numpy array внутри пайплайна, чтобы не декодировать лишний раз
        # Поэтому используем compress_bytes только для получения result, но берем image из result
        
        # Декодируем исходник
        nparr = np.frombuffer(raw_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
             raise ValueError(f"Failed to decode image: {image_path}")

        comp_result = self.compressor.compress(image, original_bytes=len(raw_bytes))
        
        # 3. Конвертируем в Grayscale / Blue Channel
        # Работаем с comp_result.image (это уже сжатый resize)
        logger.debug("[Preprocessor] Запуск Grayscale/BlueChannel conversion")
        gray_result = self.grayscale.process(comp_result.image)
        
        # 4. Кодируем результат в байты для отправки в Google Vision
        # Используем JPEG с тем же качеством, что и при сжатии
        success, buffer = cv2.imencode(".jpg", gray_result.image, [cv2.IMWRITE_JPEG_QUALITY, comp_result.quality])
        if not success:
            raise RuntimeError("Failed to encode processed image")
            
        processed_bytes = buffer.tobytes()
        
        # 5. Формируем метаданные
        metadata = {
            "original_size": comp_result.original_size,
            "processed_size": gray_result.original_size, # Это размер ПОСЛЕ сжатия (w, h)
            "compressed_size_kb": len(processed_bytes) / 1024,
            "scale_factor": comp_result.scale_factor,
            "quality": comp_result.quality,
            "grayscale_converted": gray_result.was_converted
        }
        
        return processed_bytes, metadata
