"""
OCR: Google Vision API интеграция.

Этап 2 пайплайна extraction домена:
- Отправка изображения в Google Vision
- Получение сырых результатов OCR
- Формирование RawOCRResult (контракт D1->D2)

ВАЖНО: Возвращает RawOCRResult из contracts/d1_extraction_dto.py
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.cloud import vision
from google.cloud.vision_v1 import types
from loguru import logger

from config.settings import GOOGLE_APPLICATION_CREDENTIALS, OCR_LANGUAGE_HINTS
from contracts.d1_extraction_dto import RawOCRResult, Word, BoundingBox, OCRMetadata


class GoogleVisionOCR:
    """
    Обёртка над Google Cloud Vision API.
    
    Возвращает RawOCRResult с:
    - full_text: полный текст для regex/паттернов
    - words[]: слова с координатами для layout-анализа
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Инициализация OCR клиента.
        
        Args:
            credentials_path: Путь к JSON-файлу credentials.
                            Если не указан, берётся из settings.
        """
        creds_path = credentials_path or GOOGLE_APPLICATION_CREDENTIALS
        
        if not creds_path:
            raise ValueError(
                "Google credentials не указаны!\n"
                "Укажите путь в config/settings.py или передайте в конструктор."
            )
        
        if not Path(creds_path).exists():
            raise FileNotFoundError(f"Credentials файл не найден: {creds_path}")
        
        # Устанавливаем credentials через переменную окружения
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
        
        self.client = vision.ImageAnnotatorClient()
        self.language_hints = OCR_LANGUAGE_HINTS
    
        logger.info("[GoogleVisionOCR] Клиент инициализирован")
    
    def recognize(
        self, 
        image_content: bytes, 
        source_file: str = "unknown"
    ) -> RawOCRResult:
        """
        Распознаёт текст на изображении.
        
        Args:
            image_content: Байты изображения
            source_file: Имя исходного файла (для метаданных)
            
        Returns:
            RawOCRResult: Контракт D1->D2 с full_text и words[]
        """
        logger.debug(f"[GoogleVisionOCR] Распознавание: {source_file}")
        
        image = types.Image(content=image_content)
        
        # Настройка запроса с подсказками языка
        image_context = types.ImageContext(
            language_hints=self.language_hints
        )
        
        # Выполняем DOCUMENT_TEXT_DETECTION для лучшего распознавания чеков
        response = self.client.document_text_detection(
            image=image,
            image_context=image_context
        )
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        return self._parse_response(response, source_file)
    
    def _parse_response(self, response, source_file: str) -> RawOCRResult:
        """
        Парсит ответ Google Vision в RawOCRResult.
        
        Извлекает:
        - full_text: весь текст одной строкой
        - words[]: каждое слово с координатами и confidence
        """
        words = []
        full_text = ""
        image_width = 0
        image_height = 0
        
        # Полный текст
        if response.full_text_annotation:
            full_text = response.full_text_annotation.text
        
            # Извлекаем слова с координатами
            for page in response.full_text_annotation.pages:
                # Размеры изображения
                image_width = page.width
                image_height = page.height
                
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            # Собираем текст слова
                            word_text = "".join(
                                symbol.text for symbol in word.symbols
                            )
                        
                        # Получаем bounding box
                            bbox = self._get_bounding_box(word.bounding_box)
                        
                            # Пропускаем слова с нулевыми размерами
                            if bbox["width"] <= 0 or bbox["height"] <= 0:
                                continue
                            
                            words.append(Word(
                                text=word_text,
                            bounding_box=BoundingBox(
                                x=bbox["x"],
                                y=bbox["y"],
                                width=bbox["width"],
                                height=bbox["height"]
                            ),
                                confidence=word.confidence
                            ))
        
        logger.debug(f"[GoogleVisionOCR] Извлечено слов: {len(words)}")
        
        # Формируем метаданные
        metadata = OCRMetadata(
            source_file=source_file,
            image_width=image_width or 1,  # Fallback если не определено
            image_height=image_height or 1,
            processed_at=datetime.now().isoformat(),
            preprocessing_applied=[]
        )
        
        return RawOCRResult(
            full_text=full_text,
            words=words,
            metadata=metadata
        )
    
    def _get_bounding_box(self, bounding_poly) -> dict:
        """Преобразует bounding_poly в простой bbox."""
        vertices = bounding_poly.vertices
        
        xs = [v.x for v in vertices if v.x is not None]
        ys = [v.y for v in vertices if v.y is not None]
        
        if not xs or not ys:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        x_min = min(xs)
        y_min = min(ys)
        x_max = max(xs)
        y_max = max(ys)
        
        return {
            "x": max(0, x_min),
            "y": max(0, y_min),
            "width": max(1, x_max - x_min),
            "height": max(1, y_max - y_min)
        }
    
    def recognize_from_file(self, image_path: Path) -> RawOCRResult:
        """
        Распознаёт текст из файла изображения.
        
        Args:
            image_path: Путь к файлу
            
        Returns:
            RawOCRResult: Контракт D1->D2
        """
        with open(image_path, "rb") as f:
            content = f.read()
        
        return self.recognize(content, source_file=image_path.stem)
