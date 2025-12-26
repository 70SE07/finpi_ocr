"""
Адаптер для ImagePreprocessor, реализующий интерфейс IImagePreprocessor (домен Extraction).

Позволяет использовать существующий ImagePreprocessor через единый интерфейс домена Extraction.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from loguru import logger

from ...domain.interfaces import IImagePreprocessor
from ...domain.exceptions import ImageProcessingError, ImageNotFoundError, ImageDecodingError
from ...pre_ocr.preprocessor import ImagePreprocessor as OriginalImagePreprocessor
from ...pre_ocr.elements.image_compressor import ImageCompressor
from ...pre_ocr.elements.grayscale import GrayscaleConverter


class ImagePreprocessorAdapter(IImagePreprocessor):
    """
    Адаптер для ImagePreprocessor (домен Extraction).
    
    Реализует интерфейс IImagePreprocessor, делегируя вызовы оригинальному ImagePreprocessor.
    """
    
    def __init__(
        self,
        compressor: Optional[ImageCompressor] = None,
        grayscale: Optional[GrayscaleConverter] = None
    ):
        """
        Инициализация адаптера.
        
        Args:
            compressor: Компрессор изображений (опционально)
            grayscale: Конвертер в градации серого (опционально)
        """
        try:
            self._original_preprocessor = OriginalImagePreprocessor(
                compressor=compressor,
                grayscale=grayscale
            )
            logger.debug("[Extraction] ImagePreprocessorAdapter инициализирован")
        except Exception as e:
            raise ImageProcessingError(
                message="Не удалось инициализировать ImagePreprocessor",
                component="ImagePreprocessorAdapter",
                original_error=e
            )
    
    def process(self, image_path: Path) -> Tuple[bytes, Dict[str, Any]]:
        """
        Обрабатывает изображение перед OCR.
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Кортеж: (обработанные байты, метаданные обработки)
            
        Raises:
            ImageNotFoundError: Если изображение не найдено
            ImageDecodingError: Если не удалось декодировать изображение
            ImageProcessingError: Если произошла другая ошибка обработки
        """
        try:
            logger.debug(f"[Extraction] Вызов ImagePreprocessor.process() для {image_path}")
            
            # Проверяем существование файла
            if not image_path.exists():
                raise ImageNotFoundError(
                    message=f"Изображение не найдено: {image_path}",
                    component="ImagePreprocessorAdapter"
                )
            
            # Вызываем оригинальный метод
            processed_bytes, metadata = self._original_preprocessor.process(image_path)
            
            # Добавляем дополнительную информацию в метаданные
            enhanced_metadata = {
                **metadata,
                "source_file": image_path.name,
                "file_size_kb": image_path.stat().st_size / 1024,
                "preprocessor": "ImagePreprocessorAdapter"
            }
            
            logger.debug(f"[Extraction] Изображение обработано: {image_path.name}, размер: {len(processed_bytes)} байт")
            return processed_bytes, enhanced_metadata
            
        except ImageNotFoundError:
            raise
        except Exception as e:
            # Определяем тип ошибки
            if "decode" in str(e).lower() or "decoding" in str(e).lower():
                error_class = ImageDecodingError
                error_msg = f"Ошибка декодирования изображения: {image_path}"
            else:
                error_class = ImageProcessingError
                error_msg = f"Ошибка обработки изображения: {image_path}"
            
            raise error_class(
                message=error_msg,
                component="ImagePreprocessorAdapter",
                original_error=e
            )
