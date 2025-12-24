"""
DTO для результатов OCR.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class BoundingBox:
    """Ограничивающий прямоугольник текстового блока."""
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    
    @property
    def width(self) -> int:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> int:
        return self.y_max - self.y_min
    
    @property
    def center(self) -> tuple:
        return (
            (self.x_min + self.x_max) // 2,
            (self.y_min + self.y_max) // 2
        )


@dataclass
class TextBlock:
    """Блок текста с метаданными."""
    text: str
    confidence: float  # 0.0 - 1.0
    bounding_box: Optional[BoundingBox] = None
    block_type: str = "TEXT"  # TEXT, LINE, WORD, PARAGRAPH
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": {
                "x_min": self.bounding_box.x_min,
                "y_min": self.bounding_box.y_min,
                "x_max": self.bounding_box.x_max,
                "y_max": self.bounding_box.y_max,
            } if self.bounding_box else None,
            "block_type": self.block_type
        }


@dataclass
class OcrResultDTO:
    """
    Результат OCR обработки изображения чека.
    
    Содержит:
    - Полный текст чека
    - Упорядоченные текстовые блоки (строки)
    - Метаданные обработки
    """
    
    # Основные данные
    full_text: str  # Полный текст чека (как есть от OCR)
    lines: List[TextBlock] = field(default_factory=list)  # Строки, упорядоченные сверху вниз
    items: List[dict] = field(default_factory=list)  # Распознанные товары (семантика)
    metadata: Dict[str, Any] = field(default_factory=dict) # Метаданные (Магазин, Дата и т.д.)

    
    # Метаданные
    source_file: str = ""
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ocr_confidence: float = 0.0  # Средняя уверенность OCR
    
    # Информация о пайплайне
    pre_ocr_applied: bool = False
    post_ocr_applied: bool = False
    
    # Размеры изображения
    image_width: int = 0
    image_height: int = 0
    
    def to_dict(self) -> dict:
        """Преобразует DTO в словарь."""
        return {
            "full_text": self.full_text,
            "lines": [line.to_dict() for line in self.lines],
            "items": self.items,
            "metadata": self.metadata,
            "source_file": self.source_file,
            "processed_at": self.processed_at,
            "ocr_confidence": self.ocr_confidence,
            "pre_ocr_applied": self.pre_ocr_applied,
            "post_ocr_applied": self.post_ocr_applied,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "stats": {
                "total_lines": len(self.lines),
                "total_characters": len(self.full_text),
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Сериализует DTO в JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def save(self, output_path: str) -> None:
        """Сохраняет DTO в JSON файл."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
    
    def save_txt(self, output_path: str) -> None:
        """Сохраняет только текст чека в TXT файл (для человека)."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.full_text)
    
    def save_all(self, output_dir: str, base_name: str) -> dict:
        """
        Сохраняет результат в оба формата.
        
        Args:
            output_dir: Директория для сохранения
            base_name: Базовое имя файла (без расширения)
            
        Returns:
            dict: Пути к созданным файлам
        """
        from pathlib import Path
        output_path = Path(output_dir)
        
        json_path = output_path / f"{base_name}.json"
        txt_path = output_path / f"{base_name}.txt"
        
        self.save(str(json_path))
        self.save_txt(str(txt_path))
        
        return {
            "json": str(json_path),
            "txt": str(txt_path)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OcrResultDTO":
        """Создаёт DTO из словаря."""
        lines = []
        for line_data in data.get("lines", []):
            bbox = None
            if line_data.get("bounding_box"):
                bbox = BoundingBox(**line_data["bounding_box"])
            lines.append(TextBlock(
                text=line_data["text"],
                confidence=line_data["confidence"],
                bounding_box=bbox,
                block_type=line_data.get("block_type", "TEXT")
            ))
        
        return cls(
            full_text=data["full_text"],
            lines=lines,
            source_file=data.get("source_file", ""),
            processed_at=data.get("processed_at", ""),
            ocr_confidence=data.get("ocr_confidence", 0.0),
            pre_ocr_applied=data.get("pre_ocr_applied", False),
            post_ocr_applied=data.get("post_ocr_applied", False),
            image_width=data.get("image_width", 0),
            image_height=data.get("image_height", 0),
            items=data.get("items", []),
            metadata=data.get("metadata", {})
        )
