"""
Stage 2: Script Detection

ЦКП: Определение направления текста (LTR/RTL/Vertical).

Input: CleanupResult.words[]
Output: ScriptResult(direction, script, confidence)

Текущая реализация: всегда возвращает LTR (заглушка).
TODO: Реализовать Unicode анализ для RTL/Vertical.
"""

from dataclasses import dataclass
from typing import List, Literal
from loguru import logger

from contracts.d1_extraction_dto import Word
from ..s1_ocr_cleanup.stage import CleanupResult


ScriptDirection = Literal["ltr", "rtl", "vertical"]


@dataclass
class ScriptResult:
    """
    Результат Stage 2: Script Detection.
    
    ЦКП: Направление текста для корректной сортировки в Layout.
    """
    direction: ScriptDirection = "ltr"
    script: str = "Latin"  # Latin, Arabic, Hebrew, CJK, etc.
    confidence: float = 1.0
    
    # Передаём слова дальше
    words: List[Word] = None
    
    def __post_init__(self):
        if self.words is None:
            self.words = []
    
    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "script": self.script,
            "confidence": self.confidence,
            "words_count": len(self.words),
        }


class ScriptDetectionStage:
    """
    Stage 2: Script Detection.
    
    ЦКП: Определение направления текста для Layout.
    
    Текущая реализация: всегда возвращает LTR (заглушка).
    
    TODO: Добавить модули:
    - unicode_analyzer.py - Анализ Unicode ranges для определения script
    """
    
    def __init__(self):
        """Инициализация stage."""
        pass
    
    def process(self, cleanup_result: CleanupResult) -> ScriptResult:
        """
        Определяет направление текста по словам.
        
        Args:
            cleanup_result: Результат Stage 1 (OCR Cleanup)
            
        Returns:
            ScriptResult: Направление текста
        """
        logger.debug(f"[Stage 2: Script Detection] Анализ {len(cleanup_result.words)} слов -> LTR (заглушка)")
        
        # Заглушка: всегда LTR для европейских локалей
        return ScriptResult(
            direction="ltr",
            script="Latin",
            confidence=1.0,
            words=cleanup_result.words,
        )
