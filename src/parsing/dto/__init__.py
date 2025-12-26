"""
DTO (Data Transfer Objects) для домена Parsing.

Содержит TextBlock, BoundingBox и другие внутренние DTO.
"""

from .ocr_result_dto import (
    OcrResultDTO,
    TextBlock,
    BoundingBox
)

__all__ = [
    "OcrResultDTO",
    "TextBlock", 
    "BoundingBox"
]