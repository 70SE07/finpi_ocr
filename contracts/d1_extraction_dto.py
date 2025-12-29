"""
DTO Домена 1 (Extraction).

Контракт: D1 → D2
ЦКП: Эталонный цифровой слепок текста, очищенный от физических шумов носителя.
Гарантия: 99.9% текста с чека оцифровано без потерь.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class BoundingBox:
    """Координаты текстового блока на изображении."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class TextBlock:
    """Текстовый блок (параграф) из OCR результата."""
    text: str
    confidence: float  # 0.0 - 1.0
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
    DTO Домена 1 (Extraction).
    
    Это контракт между D1 (Extraction) и D2 (Parsing).
    
    Поля:
    - full_text: Полный текст чека одной строкой
    - blocks: Текстовые блоки с координатами и confidence
    - raw_annotations: Сырые аннотации от OCR провайдера
    - metadata: Метаданные процесса (timestamp, source_file)
    
    Правила изменения:
    - Поля НЕ удаляем и НЕ переименовываем
    - Новые поля можно добавлять (backward compatible)
    - Обязательные поля: full_text, blocks
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
            } if self.metadata else None
        }
