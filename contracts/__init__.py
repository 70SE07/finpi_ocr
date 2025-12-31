"""
Контракты DTO между доменами проекта Finpi OCR.

Все контракты используют Pydantic v2 для валидации.

Контракты:
- D1 -> D2: RawOCRResult (d1_extraction_dto.py)
- D2 -> D3: RawReceiptDTO (d2_parsing_dto.py)
- D3 -> Orchestrator: ParseResultDTO (d3_categorization_dto.py)

См. README.md для детальной документации.
"""

# D1 -> D2 (Extraction -> Parsing)
from .d1_extraction_dto import RawOCRResult, Word, BoundingBox, OCRMetadata

# D2 -> D3 (Parsing -> Categorization)
from .d2_parsing_dto import RawReceiptDTO, RawReceiptItem

# D3 -> Orchestrator
from .d3_categorization_dto import (
    ParseResultDTO,
    ReceiptItem,
    ReceiptSums,
    DataValidityInfo,
)

__all__ = [
    # D1 -> D2
    "RawOCRResult",
    "Word",
    "BoundingBox",
    "OCRMetadata",
    # D2 -> D3
    "RawReceiptDTO",
    "RawReceiptItem",
    # D3 -> Orchestrator
    "ParseResultDTO",
    "ReceiptItem",
    "ReceiptSums",
    "DataValidityInfo",
]
