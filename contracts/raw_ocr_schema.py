"""
Контракт для сырых результатов OCR.

Этот модуль определяет структуру данных, которая передаётся
от домена extraction (pre-OCR + OCR) к домену parsing.

ВНИМАНИЕ: Это публичный контракт. Изменения должны быть обратно совместимы.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class BoundingBox:
    """Bounding box для текстового блока."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class TextBlock:
    """Текстовый блок (параграф) из OCR результата."""
    text: str
    confidence: float
    bounding_box: BoundingBox
    block_type: str = "PARAGRAPH"


@dataclass
class RawAnnotation:
    """Сырая аннотация от Google Vision API."""
    description: str
    bounding_poly: List[Dict[str, float]]


@dataclass
class OCRMetadata:
    """Метаданные OCR процесса."""
    timestamp: str  # ISO format datetime string
    source_file: str  # Имя исходного файла без расширения


@dataclass
class RawOCRResult:
    """
    Полный сырой результат OCR.
    
    Эта структура соответствует формату, генерируемому GoogleVisionOCR._parse_response()
    и сохраняемому в JSON файлы.
    """
    full_text: str = ""
    blocks: List[TextBlock] = field(default_factory=list)
    raw_annotations: List[RawAnnotation] = field(default_factory=list)
    metadata: Optional[OCRMetadata] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для сериализации в JSON."""
        return {
            "full_text": self.full_text,
            "blocks": [
                {
                    "text": block.text,
                    "confidence": block.confidence,
                    "bounding_box": {
                        "x": block.bounding_box.x,
                        "y": block.bounding_box.y,
                        "width": block.bounding_box.width,
                        "height": block.bounding_box.height
                    },
                    "block_type": block.block_type
                }
                for block in self.blocks
            ],
            "raw_annotations": [
                {
                    "description": ann.description,
                    "bounding_poly": ann.bounding_poly
                }
                for ann in self.raw_annotations
            ],
            "metadata": {
                "timestamp": self.metadata.timestamp if self.metadata else "",
                "source_file": self.metadata.source_file if self.metadata else ""
            } if self.metadata else {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawOCRResult":
        """Создает RawOCRResult из словаря (десериализация из JSON)."""
        metadata = None
        if data.get("metadata"):
            metadata = OCRMetadata(
                timestamp=data["metadata"].get("timestamp", ""),
                source_file=data["metadata"].get("source_file", "")
            )
        
        blocks = []
        for block_data in data.get("blocks", []):
            bbox_data = block_data.get("bounding_box", {})
            bbox = BoundingBox(
                x=bbox_data.get("x", 0.0),
                y=bbox_data.get("y", 0.0),
                width=bbox_data.get("width", 0.0),
                height=bbox_data.get("height", 0.0)
            )
            blocks.append(TextBlock(
                text=block_data.get("text", ""),
                confidence=block_data.get("confidence", 0.0),
                bounding_box=bbox,
                block_type=block_data.get("block_type", "PARAGRAPH")
            ))
        
        raw_annotations = []
        for ann_data in data.get("raw_annotations", []):
            raw_annotations.append(RawAnnotation(
                description=ann_data.get("description", ""),
                bounding_poly=ann_data.get("bounding_poly", [])
            ))
        
        return cls(
            full_text=data.get("full_text", ""),
            blocks=blocks,
            raw_annotations=raw_annotations,
            metadata=metadata
        )