"""DTO модуль - Data Transfer Objects."""

from .ocr_result_dto import OcrResultDTO, TextBlock, BoundingBox

__all__ = ["OcrResultDTO", "TextBlock", "BoundingBox"]
