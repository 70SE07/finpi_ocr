"""
Stage 1: Layout Processing

ЦКП: Преобразование words[] в упорядоченные строки.

Входные данные: RawOCRResult (words[] с координатами)
Выходные данные: LayoutResult (строки текста с координатами)

Алгоритм:
1. Группировка слов по Y-координате (в строки)
2. Сортировка слов в строке по X-координате
3. Объединение слов в текст строки
"""

from dataclasses import dataclass, field
from typing import List, Optional
from loguru import logger

from contracts.d1_extraction_dto import RawOCRResult, Word


@dataclass
class Line:
    """
    Строка текста на чеке.
    
    Результат группировки words[] по Y-координате.
    """
    text: str                           # Текст строки (слова через пробел)
    words: List[Word]                   # Исходные слова
    y_position: int                     # Y-координата строки (верхняя граница)
    x_min: int = 0                      # Левая граница строки
    x_max: int = 0                      # Правая граница строки
    confidence: float = 1.0             # Средняя уверенность слов
    line_number: int = 0                # Номер строки (сверху вниз)
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "y_position": self.y_position,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "confidence": self.confidence,
            "line_number": self.line_number,
            "words_count": len(self.words),
        }


@dataclass
class LayoutResult:
    """
    Результат Stage 1: Layout Processing.
    
    ЦКП: Упорядоченные строки текста с координатами.
    """
    lines: List[Line] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    total_words: int = 0
    
    @property
    def full_text(self) -> str:
        """Полный текст (все строки через перенос)."""
        return "\n".join(line.text for line in self.lines)
    
    @property
    def texts(self) -> List[str]:
        """Список текстов строк."""
        return [line.text for line in self.lines]
    
    def to_dict(self) -> dict:
        return {
            "lines": [line.to_dict() for line in self.lines],
            "image_width": self.image_width,
            "image_height": self.image_height,
            "total_words": self.total_words,
            "total_lines": len(self.lines),
        }


class LayoutStage:
    """
    Stage 1: Layout Processing.
    
    ЦКП: Преобразование words[] в упорядоченные строки.
    
    Использует Y-координаты для группировки слов в строки,
    X-координаты для сортировки слов внутри строки.
    """
    
    def __init__(self, y_threshold: int = 15):
        """
        Args:
            y_threshold: Максимальная разница Y для объединения в строку (px).
                        Слова с разницей Y <= threshold считаются одной строкой.
        """
        self.y_threshold = y_threshold
    
    def process(self, raw_ocr: RawOCRResult) -> LayoutResult:
        """
        Обрабатывает RawOCRResult и возвращает LayoutResult.
        
        Args:
            raw_ocr: Результат D1 (Extraction)
            
        Returns:
            LayoutResult: Строки с координатами
        """
        logger.debug(f"[Stage 1: Layout] Обработка {len(raw_ocr.words)} слов")
        
        if not raw_ocr.words:
            logger.warning("[Stage 1: Layout] Нет слов для обработки")
            return LayoutResult(
                image_width=raw_ocr.metadata.image_width if raw_ocr.metadata else 0,
                image_height=raw_ocr.metadata.image_height if raw_ocr.metadata else 0,
            )
        
        # Группируем слова в строки
        grouped_lines = self._group_words_into_lines(raw_ocr.words)
        
        # Создаём Line объекты
        lines = []
        for i, words_in_line in enumerate(grouped_lines):
            line = self._create_line(words_in_line, line_number=i)
            lines.append(line)
        
        result = LayoutResult(
            lines=lines,
            image_width=raw_ocr.metadata.image_width if raw_ocr.metadata else 0,
            image_height=raw_ocr.metadata.image_height if raw_ocr.metadata else 0,
            total_words=len(raw_ocr.words),
        )
        
        logger.info(f"[Stage 1: Layout] Результат: {len(lines)} строк из {len(raw_ocr.words)} слов")
        
        return result
    
    def _group_words_into_lines(self, words: List[Word]) -> List[List[Word]]:
        """
        Группирует слова в строки по Y-координате.
        
        Алгоритм:
        1. Сортируем слова по Y
        2. Объединяем слова с близкими Y в одну строку
        3. Сортируем слова в строке по X
        """
        if not words:
            return []
        
        # Сортируем по Y (сверху вниз)
        sorted_words = sorted(words, key=lambda w: w.bounding_box.y)
        
        lines: List[List[Word]] = []
        current_line: List[Word] = [sorted_words[0]]
        current_y = sorted_words[0].bounding_box.y
        
        for word in sorted_words[1:]:
            word_y = word.bounding_box.y
            
            # Если слово на той же строке (Y близко)
            if abs(word_y - current_y) <= self.y_threshold:
                current_line.append(word)
            else:
                # Сортируем текущую строку по X и добавляем
                current_line.sort(key=lambda w: w.bounding_box.x)
                lines.append(current_line)
                
                # Начинаем новую строку
                current_line = [word]
                current_y = word_y
        
        # Добавляем последнюю строку
        if current_line:
            current_line.sort(key=lambda w: w.bounding_box.x)
            lines.append(current_line)
        
        return lines
    
    def _create_line(self, words: List[Word], line_number: int) -> Line:
        """Создаёт Line из списка слов."""
        # Текст строки
        text = " ".join(word.text for word in words)
        
        # Координаты
        y_position = min(w.bounding_box.y for w in words)
        x_min = min(w.bounding_box.x for w in words)
        x_max = max(w.bounding_box.x + w.bounding_box.width for w in words)
        
        # Средняя уверенность
        confidence = sum(w.confidence for w in words) / len(words) if words else 0.0
        
        return Line(
            text=text,
            words=words,
            y_position=y_position,
            x_min=x_min,
            x_max=x_max,
            confidence=confidence,
            line_number=line_number,
        )
