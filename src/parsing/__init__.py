"""
Домен Parsing (D2): Обработка сырых результатов OCR.

Архитектура: 8-этапный пайплайн
- Stage 1: OCR Cleanup (очистка OCR-артефактов)
- Stage 2: Script Detection (определение направления текста)
- Stage 3: Layout (группировка слов в строки)
- Stage 4: Locale Detection (определение локали)
- Stage 5: Store Detection (определение магазина)
- Stage 6: Metadata (дата, сумма, валюта)
- Stage 7: Semantic (извлечение товаров)
- Stage 8: Validation (checksum)

Вход: contracts.RawOCRResult (от D1)
Выход: contracts.RawReceiptDTO (для D3)
"""

from src.parsing.pipeline import ParsingPipeline, PipelineResult
from src.parsing.locales.config_loader import ConfigLoader

# Stage exports
from src.parsing.s1_ocr_cleanup import OCRCleanupStage, CleanupResult
from src.parsing.s2_script_detection import ScriptDetectionStage, ScriptResult
from src.parsing.s3_layout import LayoutStage, LayoutResult, Line
from src.parsing.s4_locale_detection import LocaleDetectionStage, LocaleResult
from src.parsing.s5_store_detection import StoreDetectionStage, StoreResult
from src.parsing.s6_metadata import MetadataStage, MetadataResult
from src.parsing.s7_semantic import SemanticStage, SemanticResult, ParsedItem
from src.parsing.s8_validation import ValidationStage, ValidationResult

__all__ = [
    # Pipeline
    "ParsingPipeline",
    "PipelineResult",
    "ConfigLoader",
    # Stages
    "OCRCleanupStage",
    "CleanupResult",
    "ScriptDetectionStage",
    "ScriptResult",
    "LayoutStage",
    "LayoutResult",
    "Line",
    "LocaleDetectionStage",
    "LocaleResult",
    "StoreDetectionStage",
    "StoreResult",
    "MetadataStage",
    "MetadataResult",
    "SemanticStage",
    "SemanticResult",
    "ParsedItem",
    "ValidationStage",
    "ValidationResult",
]
