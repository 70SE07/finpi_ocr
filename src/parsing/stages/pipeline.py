"""
Parsing Pipeline - Оркестратор 6 этапов D2.

Координирует выполнение всех этапов в строгом порядке:
1. Layout → 2. Locale → 3. Store → 4. Metadata → 5. Semantic → 6. Validation

Возвращает RawReceiptDTO (контракт D2->D3).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from contracts.d1_extraction_dto import RawOCRResult
from contracts.d2_parsing_dto import RawReceiptDTO, RawReceiptItem

from .stage_1_layout import LayoutStage, LayoutResult
from .stage_2_locale import LocaleStage, LocaleResult
from .stage_3_store import StoreStage, StoreResult
from .stage_4_metadata import MetadataStage, MetadataResult
from .stage_5_semantic import SemanticStage, SemanticResult
from .stage_6_validation import ValidationStage, ValidationResult

# Конфигурационный загрузчик для локалей
from ..locales.config_loader import ConfigLoader


@dataclass
class PipelineResult:
    """
    Полный результат пайплайна со всеми промежуточными данными.
    
    Используется для отладки и анализа.
    """
    # Финальный результат (контракт D2->D3)
    dto: RawReceiptDTO
    
    # Промежуточные результаты этапов
    layout: Optional[LayoutResult] = None
    locale: Optional[LocaleResult] = None
    store: Optional[StoreResult] = None
    metadata: Optional[MetadataResult] = None
    semantic: Optional[SemanticResult] = None
    validation: Optional[ValidationResult] = None
    
    # Метрики
    processing_time_ms: float = 0.0
    stages_completed: int = 0
    
    def to_dict(self) -> dict:
        return {
            "dto": self.dto.model_dump() if self.dto else None,
            "layout": self.layout.to_dict() if self.layout else None,
            "locale": self.locale.to_dict() if self.locale else None,
            "store": self.store.to_dict() if self.store else None,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "semantic": self.semantic.to_dict() if self.semantic else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "processing_time_ms": self.processing_time_ms,
            "stages_completed": self.stages_completed,
        }


class ParsingPipeline:
    """
    Пайплайн парсинга D2.
    
    Координирует 6 этапов в строгом порядке:
    1. Layout Processing
    2. Locale Detection
    3. Store Detection
    4. Metadata Extraction
    5. Semantic Extraction
    6. Validation
    
    ЦКП: RawReceiptDTO с валидированными данными.
    """
    
    def __init__(
        self,
        layout_stage: Optional[LayoutStage] = None,
        locale_stage: Optional[LocaleStage] = None,
        store_stage: Optional[StoreStage] = None,
        metadata_stage: Optional[MetadataStage] = None,
        semantic_stage: Optional[SemanticStage] = None,
        validation_stage: Optional[ValidationStage] = None,
        config_loader: Optional[ConfigLoader] = None,
    ):
        """
        Инициализация пайплайна.
        
        Args:
            Все этапы опциональны — по умолчанию создаются стандартные.
            config_loader: Загрузчик конфигов локалей
        """
        self.layout_stage = layout_stage or LayoutStage()
        self.locale_stage = locale_stage or LocaleStage()
        self.store_stage = store_stage or StoreStage()
        self.metadata_stage = metadata_stage or MetadataStage(config_loader=config_loader)
        self.semantic_stage = semantic_stage or SemanticStage(config_loader=config_loader)
        self.validation_stage = validation_stage or ValidationStage()
        
        logger.info("[ParsingPipeline] Инициализирован (6 этапов с ConfigLoader)")
    
    def process(self, raw_ocr: RawOCRResult) -> PipelineResult:
        """
        Обрабатывает RawOCRResult через все 6 этапов.
        
        Args:
            raw_ocr: Результат D1 (Extraction)
            
        Returns:
            PipelineResult: Полный результат с DTO и промежуточными данными
        """
        import time
        start_time = time.time()
        
        source_file = raw_ocr.metadata.source_file if raw_ocr.metadata else "unknown"
        logger.info(f"[ParsingPipeline] Старт обработки: {source_file}")
        
        stages_completed = 0
        
        # Stage 1: Layout
        logger.debug("[ParsingPipeline] Stage 1/6: Layout")
        layout = self.layout_stage.process(raw_ocr)
        stages_completed += 1
        
        # Stage 2: Locale
        logger.debug("[ParsingPipeline] Stage 2/6: Locale")
        locale = self.locale_stage.process(layout)
        stages_completed += 1
        
        # Stage 3: Store
        logger.debug("[ParsingPipeline] Stage 3/6: Store")
        store = self.store_stage.process(layout, locale)
        stages_completed += 1
        
        # Stage 4: Metadata
        logger.debug("[ParsingPipeline] Stage 4/6: Metadata")
        metadata = self.metadata_stage.process(layout, locale, store)
        stages_completed += 1
        
        # Stage 5: Semantic
        logger.debug("[ParsingPipeline] Stage 5/6: Semantic")
        semantic = self.semantic_stage.process(layout, locale, store, metadata)
        stages_completed += 1
        
        # Stage 6: Validation
        logger.debug("[ParsingPipeline] Stage 6/6: Validation")
        validation = self.validation_stage.process(semantic, metadata)
        stages_completed += 1
        
        # Собираем DTO
        dto = self._build_dto(
            raw_ocr=raw_ocr,
            locale=locale,
            store=store,
            metadata=metadata,
            semantic=semantic,
            validation=validation,
        )
        
        # Время обработки
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"[ParsingPipeline] Завершено за {processing_time_ms:.1f}ms: "
            f"{len(semantic.items)} товаров, validation={validation.passed}"
        )
        
        return PipelineResult(
            dto=dto,
            layout=layout,
            locale=locale,
            store=store,
            metadata=metadata,
            semantic=semantic,
            validation=validation,
            processing_time_ms=processing_time_ms,
            stages_completed=stages_completed,
        )
    
    def _build_dto(
        self,
        raw_ocr: RawOCRResult,
        locale: LocaleResult,
        store: StoreResult,
        metadata: MetadataResult,
        semantic: SemanticResult,
        validation: ValidationResult,
    ) -> RawReceiptDTO:
        """Собирает RawReceiptDTO из результатов этапов."""
        
        # Конвертируем ParsedItem в RawReceiptItem
        items = []
        for item in semantic.items:
            items.append(RawReceiptItem(
                name=item.name,
                quantity=item.quantity,
                price=item.price,
                total=item.total,
                date=datetime.combine(metadata.receipt_date, datetime.min.time()) 
                     if metadata.receipt_date else None,
            ))
        
        return RawReceiptDTO(
            items=items,
            total_amount=metadata.receipt_total,
            merchant=store.store_name,
            store_address=store.store_address,
            date=datetime.combine(metadata.receipt_date, datetime.min.time()) 
                 if metadata.receipt_date else None,
            receipt_id=raw_ocr.metadata.source_file if raw_ocr.metadata else None,
            ocr_text=raw_ocr.full_text,
            detected_locale=locale.locale_code,
            metrics={
                "processing_time_ms": 0.0,  # Заполнится в PipelineResult
                "items_count": len(semantic.items),
                "validation_passed": validation.passed,
                "validation_difference": validation.difference,
            },
        )
