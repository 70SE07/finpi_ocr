"""
Stage 1: OCR Cleanup

ЦКП: Очистка слов от OCR-артефактов.

Input: RawOCRResult.words[]
Output: CleanupResult(words[]) - очищенные слова

Текущая реализация: pass-through (заглушка).
TODO: Реализовать модули очистки.
"""

from dataclasses import dataclass, field
from typing import List
from loguru import logger

from contracts.d1_extraction_dto import RawOCRResult, Word


@dataclass
class CleanupResult:
    """
    Результат Stage 1: OCR Cleanup.
    
    ЦКП: Очищенные слова без OCR-артефактов.
    """
    words: List[Word] = field(default_factory=list)
    original_count: int = 0
    cleaned_count: int = 0
    removed_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "words_count": len(self.words),
            "original_count": self.original_count,
            "cleaned_count": self.cleaned_count,
            "removed_count": self.removed_count,
        }


class OCRCleanupStage:
    """
    Stage 1: OCR Cleanup.
    
    ЦКП: Очистка слов от OCR-артефактов.
    
    Текущая реализация: pass-through (заглушка).
    Слова передаются без изменений для сохранения работоспособности pipeline.
    
    TODO: Добавить модули:
    - char_replacer.py - Замена похожих символов (0->O, 1->l)
    - word_merger.py - Склейка разорванных слов ("LI DL" -> "LIDL")
    - word_splitter.py - Разделение склеенных ("LIDL6,99" -> "LIDL", "6,99")
    - garbage_filter.py - Удаление мусорных символов
    - unicode_normalizer.py - Нормализация Unicode
    """
    
    def __init__(self):
        """Инициализация stage."""
        pass
    
    def process(self, raw_ocr: RawOCRResult) -> CleanupResult:
        """
        Обрабатывает RawOCRResult и возвращает CleanupResult.
        
        Args:
            raw_ocr: Результат D1 (Extraction)
            
        Returns:
            CleanupResult: Очищенные слова
        """
        logger.debug(f"[Stage 1: OCR Cleanup] Pass-through {len(raw_ocr.words)} слов")
        
        # Pass-through: передаём слова без изменений
        return CleanupResult(
            words=raw_ocr.words,
            original_count=len(raw_ocr.words),
            cleaned_count=len(raw_ocr.words),
            removed_count=0,
        )
