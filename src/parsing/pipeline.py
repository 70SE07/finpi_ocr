"""
Parsing Pipeline - Оркестратор 8 этапов D2.

Координирует выполнение всех этапов в строгом порядке:
1. OCR Cleanup → 2. Script Detection → 3. Layout → 4. Locale → 
5. Store → 6. Metadata → 7. Semantic → 8. Validation

Возвращает RawReceiptDTO (контракт D2->D3).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from contracts.d1_extraction_dto import RawOCRResult
from contracts.d2_parsing_dto import RawReceiptDTO, RawReceiptItem

# Stage imports
from .s1_ocr_cleanup import OCRCleanupStage, CleanupResult
from .s2_script_detection import ScriptDetectionStage, ScriptResult
from .s3_layout import LayoutStage, LayoutResult, Line
from .s4_locale_detection import LocaleDetectionStage, LocaleResult
from .s5_store_detection import StoreDetectionStage, StoreResult
from .s6_metadata import MetadataStage, MetadataResult
from .s7_semantic import SemanticStage, SemanticResult, ParsedItem
from .s8_validation import ValidationStage, ValidationResult

# Config loader
from .locales.config_loader import ConfigLoader


@dataclass
class PipelineResult:
    """
    Полный результат пайплайна со всеми промежуточными данными.
    
    Используется для отладки и анализа.
    """
    # Финальный результат (контракт D2->D3)
    dto: RawReceiptDTO
    
    # Промежуточные результаты этапов
    cleanup: Optional[CleanupResult] = None
    script: Optional[ScriptResult] = None
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
            "cleanup": self.cleanup.to_dict() if self.cleanup else None,
            "script": self.script.to_dict() if self.script else None,
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
    
    Координирует 8 этапов в строгом порядке:
    1. OCR Cleanup - очистка слов от OCR-артефактов
    2. Script Detection - определение направления текста
    3. Layout Processing - построение строк
    4. Locale Detection - определение локали
    5. Store Detection - определение магазина
    6. Metadata Extraction - извлечение даты и суммы
    7. Semantic Extraction - извлечение товаров
    8. Validation - checksum
    
    ЦКП: RawReceiptDTO с валидированными данными.
    """
    
    def __init__(
        self,
        ocr_cleanup_stage: Optional[OCRCleanupStage] = None,
        script_detection_stage: Optional[ScriptDetectionStage] = None,
        layout_stage: Optional[LayoutStage] = None,
        locale_stage: Optional[LocaleDetectionStage] = None,
        store_stage: Optional[StoreDetectionStage] = None,
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
        self.config_loader = config_loader or ConfigLoader()
        
        self.ocr_cleanup_stage = ocr_cleanup_stage or OCRCleanupStage()
        self.script_detection_stage = script_detection_stage or ScriptDetectionStage()
        self.layout_stage = layout_stage or LayoutStage()
        self.locale_stage = locale_stage or LocaleDetectionStage(config_loader=self.config_loader)
        self.store_stage = store_stage or StoreDetectionStage(config_loader=self.config_loader)
        self.metadata_stage = metadata_stage or MetadataStage(config_loader=self.config_loader)
        self.semantic_stage = semantic_stage or SemanticStage(config_loader=self.config_loader)
        self.validation_stage = validation_stage or ValidationStage()
        
        logger.info("[ParsingPipeline] Инициализирован (8 этапов)")
    
    def process(self, raw_ocr: RawOCRResult) -> PipelineResult:
        """
        Обрабатывает RawOCRResult через все 8 этапов.
        
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
        
        # Stage 1: OCR Cleanup
        logger.debug("[ParsingPipeline] Stage 1/8: OCR Cleanup")
        cleanup = self.ocr_cleanup_stage.process(raw_ocr)
        stages_completed += 1
        
        # Stage 2: Script Detection
        logger.debug("[ParsingPipeline] Stage 2/8: Script Detection")
        script = self.script_detection_stage.process(cleanup)
        stages_completed += 1
        
        # Stage 3: Layout
        logger.debug("[ParsingPipeline] Stage 3/8: Layout")
        layout = self.layout_stage.process(script, raw_ocr)
        stages_completed += 1
        
        # Stage 4: Locale
        logger.debug("[ParsingPipeline] Stage 4/8: Locale")
        locale = self.locale_stage.process(layout)
        stages_completed += 1
        
        # Stage 5: Store
        logger.debug("[ParsingPipeline] Stage 5/8: Store")
        store = self.store_stage.process(layout, locale)
        stages_completed += 1
        
        # Stage 6: Metadata
        logger.debug("[ParsingPipeline] Stage 6/8: Metadata")
        metadata = self.metadata_stage.process(layout, locale, store)
        stages_completed += 1
        
        # Stage 7: Semantic
        logger.debug("[ParsingPipeline] Stage 7/8: Semantic")
        semantic = self.semantic_stage.process(layout, locale, store, metadata)
        stages_completed += 1
        
        # Stage 8: Validation
        logger.debug("[ParsingPipeline] Stage 8/8: Validation")
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
            cleanup=cleanup,
            script=script,
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
                raw_text=item.raw_text,
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
