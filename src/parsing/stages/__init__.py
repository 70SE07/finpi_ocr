"""
6 этапов пайплайна D2 (Parsing) по ADR-015.

Порядок выполнения строгий:
1. Layout Processing - группировка words[] в строки
2. Locale Detection - определение локали по тексту
3. Store Detection - определение магазина
4. Metadata Extraction - дата, сумма, адрес
5. Semantic Extraction - извлечение товаров
6. Validation - checksum валидация

Каждый этап имеет:
- Свой ЦКП (Central End Product)
- Единственную ответственность (SRP)
- Интерфейс для тестирования
"""

from .stage_1_layout import LayoutStage, LayoutResult, Line
from .stage_2_locale import LocaleStage, LocaleResult
from .stage_3_store import StoreStage, StoreResult
from .stage_4_metadata import MetadataStage, MetadataResult
from .stage_5_semantic import SemanticStage, SemanticResult, ParsedItem
from .stage_6_validation import ValidationStage, ValidationResult
from .pipeline import ParsingPipeline, PipelineResult

__all__ = [
    # Pipeline
    "ParsingPipeline",
    "PipelineResult",
    # Stage 1
    "LayoutStage",
    "LayoutResult",
    "Line",
    # Stage 2
    "LocaleStage",
    "LocaleResult",
    # Stage 3
    "StoreStage",
    "StoreResult",
    # Stage 4
    "MetadataStage",
    "MetadataResult",
    # Stage 5
    "SemanticStage",
    "SemanticResult",
    "ParsedItem",
    # Stage 6
    "ValidationStage",
    "ValidationResult",
]
