"""
Домен Parsing (D2): Обработка сырых результатов OCR.

Архитектура: 6-этапный пайплайн (ADR-015)
- Stage 1: Layout (группировка слов в строки)
- Stage 2: Locale (определение языка/локали)
- Stage 3: Store (определение магазина)
- Stage 4: Metadata (дата, сумма, валюта)
- Stage 5: Semantic (извлечение товаров)
- Stage 6: Validation (checksum)

Вход: contracts.RawOCRResult (от D1)
Выход: contracts.RawReceiptDTO (для D3)
"""

from src.parsing.stages.pipeline import ParsingPipeline
from src.parsing.locales.config_loader import ConfigLoader

__all__ = [
    "ParsingPipeline",
    "ConfigLoader",
]