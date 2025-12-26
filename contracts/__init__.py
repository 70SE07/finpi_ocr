"""
Контракты между доменами проекта Finpi OCR.

Этот пакет определяет границы между доменами:
- extraction (pre-OCR + OCR) → raw_ocr_results.json
- parsing (обработка raw OCR) → структурированные данные

Основной контракт: RawOCRResult в raw_ocr_schema.py
"""

from .raw_ocr_schema import RawOCRResult

__all__ = ["RawOCRResult"]