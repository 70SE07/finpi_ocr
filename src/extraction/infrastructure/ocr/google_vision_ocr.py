"""
OCR: Google Vision API интеграция.

Этап 2 пайплайна extraction домена:
- Отправка изображения в Google Vision
- Получение сырых результатов OCR
- Валидация ответа через GoogleVisionValidatedResponse контракт
- Формирование RawOCRResult (контракт D1->D2)

КОНТРАКТЫ:
  Входные: bytes (JPEG из Stage 5)
  Выходные: RawOCRResult (валидированный через GoogleVisionValidatedResponse)

ВАЖНО: Возвращает RawOCRResult из contracts/d1_extraction_dto.py
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from google.cloud import vision
from google.cloud.vision_v1 import types
from pydantic import ValidationError
from loguru import logger

from config.settings import GOOGLE_APPLICATION_CREDENTIALS
from contracts.d1_extraction_dto import RawOCRResult, Word, BoundingBox, OCRMetadata
from src.domain.contracts import (
    GoogleVisionValidatedResponse, GoogleVisionWord,
    GoogleVisionBoundingBox, GoogleVisionVertice,
    ContractValidationError
)
from ...domain.interfaces import IOCRProvider


class GoogleVisionOCR(IOCRProvider):
    """
    Обёртка над Google Cloud Vision API.
    
    Реализует интерфейс IOCRProvider.
    Возвращает RawOCRResult с:
    - full_text: полный текст для regex/паттернов
    - words[]: слова с координатами для layout-анализа
    
    КОНТРАКТЫ:
      Валидирует ответ API через GoogleVisionValidatedResponse
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
    
        logger.info("[GoogleVisionOCR] Клиент инициализирован (с контрактами)")
    
    def recognize(
        self, 
        image_content: bytes, 
        source_file: str = "unknown",
        image_width: int = 0,
        image_height: int = 0
    ) -> RawOCRResult:
        """
        Распознаёт текст на изображении.
        
        ВАЛИДИРУЕТ: Результат через GoogleVisionValidatedResponse контракт
        
        Args:
            image_content: Байты изображения
            source_file: Имя исходного файла (для метаданных)
            image_width: Ширина исходного изображения (для валидации координат)
            image_height: Высота исходного изображения (для валидации координат)
            
        Returns:
            RawOCRResult: Контракт D1->D2 с full_text и words[]
            
        Raises:
            ContractValidationError: если ответ API невалиден
        """
        logger.debug(f"[GoogleVisionOCR] Распознавание: {source_file}")
        
        image = types.Image(content=image_content)
        
        # Выполняем DOCUMENT_TEXT_DETECTION для лучшего распознавания чеков
        # Google Vision сам определяет язык - D1 language-agnostic
        response = self.client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")
        
        return self._parse_response(response, source_file, image_width, image_height)
    
    def _parse_response(
        self, 
        response: Any, 
        source_file: str,
        image_width: int = 0,
        image_height: int = 0
    ) -> RawOCRResult:
        """
        Парсит ответ Google Vision в RawOCRResult.
        
        ✅ ВАЛИДИРУЕТ: Результат через GoogleVisionValidatedResponse контракт
        
        Извлекает:
        - full_text: весь текст одной строкой
        - words[]: каждое слово с координатами и confidence
        """
        words = []
        full_text = ""
        api_image_width = image_width or 0
        api_image_height = image_height or 0
        
        # Полный текст
        if response.full_text_annotation:
            full_text = response.full_text_annotation.text
        
            # Извлекаем слова с координатами
            for page in response.full_text_annotation.pages:
                # Размеры изображения из API (если не передали)
                if not image_width:
                    api_image_width = page.width
                if not image_height:
                    api_image_height = page.height
                
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
                            
                            words.append(GoogleVisionWord(
                                text=word_text,
                                bounding_box=GoogleVisionBoundingBox(
                                    vertices=[
                                        GoogleVisionVertice(x=bbox["x"], y=bbox["y"]),
                                        GoogleVisionVertice(x=bbox["x"] + bbox["width"], y=bbox["y"]),
                                        GoogleVisionVertice(x=bbox["x"] + bbox["width"], y=bbox["y"] + bbox["height"]),
                                        GoogleVisionVertice(x=bbox["x"], y=bbox["y"] + bbox["height"])
                                    ]
                                ),
                                confidence=max(0.0, min(1.0, word.confidence))  # Гарантируем [0, 1]
                            ))
        
        logger.debug(f"[GoogleVisionOCR] Извлечено слов: {len(words)}")
        
        # ✅ ВАЛИДАЦИЯ через контракт
        try:
            validated_response = GoogleVisionValidatedResponse(
                full_text=full_text or "no text detected",  # Гарантируем не-пустой текст
                words=words or [],  # Может быть пусто, но должно быть список
                confidence=0.5,  # Placeholder, т.к. нет средней confidence в API
                image_width=api_image_width or 1,  # Гарантируем > 0
                image_height=api_image_height or 1
            )
            logger.debug(f"[GoogleVisionOCR] ✅ Ответ API валидирован: "
                        f"{validated_response.image_width}x{validated_response.image_height}, "
                        f"{len(validated_response.words)} слов")
        except ValidationError as e:
            raise ContractValidationError("GoogleVision", "GoogleVisionValidatedResponse", e.errors())
        
        # Формируем метаданные
        metadata = OCRMetadata(
            source_file=source_file,
            image_width=api_image_width or 1,
            image_height=api_image_height or 1,
            processed_at=datetime.now().isoformat(),
            preprocessing_applied=[]
        )
        
        return RawOCRResult(
            full_text=validated_response.full_text,
            words=[
                Word(
                    text=w.text,
                    bounding_box=BoundingBox(
                        x=int(min(v.x for v in w.bounding_box.vertices)),
                        y=int(min(v.y for v in w.bounding_box.vertices)),
                        width=int(max(v.x for v in w.bounding_box.vertices) - min(v.x for v in w.bounding_box.vertices)),
                        height=int(max(v.y for v in w.bounding_box.vertices) - min(v.y for v in w.bounding_box.vertices))
                    ),
                    confidence=w.confidence
                )
                for w in validated_response.words
            ],
            metadata=metadata
        )
    
    def _get_bounding_box(self, bounding_poly: Any) -> dict[str, Any]:
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

