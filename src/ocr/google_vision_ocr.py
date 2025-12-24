"""
OCR: Google Vision API интеграция.

Этап 2 пайплайна:
- Отправка изображения в Google Vision
- Получение сырых результатов OCR
- Сохранение raw_ocr в JSON для аналитики
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from google.cloud import vision
from google.cloud.vision_v1 import types

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GOOGLE_APPLICATION_CREDENTIALS, OCR_LANGUAGE_HINTS, OUTPUT_DIR


class GoogleVisionOCR:
    """Обёртка над Google Cloud Vision API."""
    
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
    
    def recognize(self, image_content: bytes) -> dict:
        """
        Распознаёт текст на изображении.
        
        Args:
            image_content: Байты изображения
            
        Returns:
            dict: Сырой результат от Google Vision
        """
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
        
        return self._parse_response(response)
    
    def _parse_response(self, response) -> dict:
        """Парсит ответ Google Vision в структурированные данные."""
        result = {
            "full_text": "",
            "blocks": [],
            "raw_annotations": []
        }
        
        # Полный текст
        if response.full_text_annotation:
            result["full_text"] = response.full_text_annotation.text
        
        # Обрабатываем блоки текста
        if response.full_text_annotation:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        # Собираем текст параграфа
                        para_text = ""
                        para_confidence = 0.0
                        word_count = 0
                        
                        for word in paragraph.words:
                            word_text = "".join(
                                symbol.text for symbol in word.symbols
                            )
                            para_text += word_text + " "
                            para_confidence += word.confidence
                            word_count += 1
                        
                        para_text = para_text.strip()
                        avg_confidence = para_confidence / word_count if word_count > 0 else 0.0
                        
                        # Получаем bounding box
                        bbox = self._get_bounding_box(paragraph.bounding_box)
                        
                        result["blocks"].append({
                            "text": para_text,
                            "confidence": avg_confidence,
                            "bounding_box": bbox,
                            "block_type": "PARAGRAPH"
                        })
        
        # Сохраняем raw annotations для отладки
        for annotation in response.text_annotations:
            result["raw_annotations"].append({
                "description": annotation.description,
                "bounding_poly": [
                    {"x": v.x, "y": v.y} 
                    for v in annotation.bounding_poly.vertices
                ]
            })
        
        return result
    
    def _get_bounding_box(self, bounding_poly) -> dict:
        """Преобразует bounding_poly в простой bbox."""
        vertices = bounding_poly.vertices
        
        xs = [v.x for v in vertices]
        ys = [v.y for v in vertices]
        
        return {
            "x_min": min(xs),
            "y_min": min(ys),
            "x_max": max(xs),
            "y_max": max(ys)
        }
    
    def recognize_from_file(self, image_path: Path) -> dict:
        """
        Распознаёт текст из файла изображения.
        
        Args:
            image_path: Путь к файлу
            
        Returns:
            dict: Результат OCR
        """
        with open(image_path, "rb") as f:
            content = f.read()
        
        return self.recognize(content)
    
    def save_raw_ocr(self, result: dict, filename: str) -> Path:
        """
        Сохраняет сырой результат OCR в JSON файл.
        
        Args:
            result: Результат OCR (dict)
            filename: Имя файла (без расширения)
            
        Returns:
            Path: Путь к сохранённому файлу
        """
        raw_ocr_dir = OUTPUT_DIR / "raw_ocr"
        raw_ocr_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = raw_ocr_dir / f"{filename}.json"
        
        # Добавляем метаданные
        result_with_meta = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source_file": filename,
            },
            **result
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_with_meta, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def recognize_and_save(self, image_content: bytes, filename: str) -> tuple[dict, Path]:
        """
        Распознаёт текст и сохраняет raw результат в JSON.
        
        Args:
            image_content: Байты изображения
            filename: Имя исходного файла (без расширения)
            
        Returns:
            tuple: (результат OCR, путь к JSON файлу)
        """
        result = self.recognize(image_content)
        json_path = self.save_raw_ocr(result, filename)
        return result, json_path
    
    def recognize_from_file_and_save(self, image_path: Path) -> tuple[dict, Path]:
        """
        Распознаёт текст из файла и сохраняет raw результат.
        
        Args:
            image_path: Путь к изображению
            
        Returns:
            tuple: (результат OCR, путь к JSON файлу)
        """
        with open(image_path, "rb") as f:
            content = f.read()
        
        filename = image_path.stem  # Имя без расширения
        return self.recognize_and_save(content, filename)

