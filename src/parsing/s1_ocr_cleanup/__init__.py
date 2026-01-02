"""
Stage 1: OCR Cleanup

ЦКП: Очистка слов от OCR-артефактов.
"""

from .stage import OCRCleanupStage, CleanupResult

__all__ = ["OCRCleanupStage", "CleanupResult"]
