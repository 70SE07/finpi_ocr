"""
DTO контракт: D1 (Extraction) -> D2 (Parsing)

Результат OCR обработки изображения чека.
Содержит полный текст И слова с координатами для максимального качества парсинга.

ВАЖНО: Это НАША зона свободы. Мы авторы этого контракта.
Оптимизируем для достижения 99.9% качества парсинга.

Решение: ADR-006 - передавать и full_text, и words[] с координатами.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BoundingBox:
    """
    Координаты слова на изображении.
    """
    x: int          # Левый верхний угол X
    y: int          # Левый верхний угол Y
    width: int      # Ширина
    height: int     # Высота


@dataclass
class Word:
    """
    Отдельное слово распознанное OCR.
    
    Используется для:
    - Понимания layout (где левая колонка, где правая)
    - Разделения названия товара от цены по X-координате
    - Группировки слов в строки по Y-координате
    - Понимания качества распознавания (confidence)
    """
    text: str                    # Текст слова
    bounding_box: BoundingBox    # Координаты на изображении
    confidence: float = 1.0      # Уверенность OCR (0.0 - 1.0)


@dataclass
class OCRMetadata:
    """
    Метаданные OCR обработки.
    """
    source_file: str                              # Имя исходного файла
    image_width: int                              # Ширина изображения (px)
    image_height: int                             # Высота изображения (px)
    processed_at: str                             # Timestamp обработки (ISO 8601)
    preprocessing_applied: List[str] = field(default_factory=list)  # Что применено (grayscale, deskew, etc.)


@dataclass
class RawOCRResult:
    """
    Результат OCR обработки изображения.
    
    Содержит ДВА представления данных:
    1. full_text - для быстрых regex, поиска паттернов, определения локали
    2. words[] - для понимания layout, структуры, точного извлечения
    
    Это дает D2 максимум информации для достижения 99.9% качества.
    
    Примеры использования:
    
    # Быстрый поиск локали
    if "zu zahlen" in raw_ocr.full_text.lower():
        locale = "de_DE"
    
    # Точное извлечение цен (правая колонка)
    for word in raw_ocr.words:
        if word.bounding_box.x > image_width * 0.7:
            prices.append(word.text)
    """
    
    # Полный текст одной строкой
    # Используется для: regex, поиска паттернов, определения локали
    full_text: str = ""
    
    # Слова с координатами
    # Используется для: layout, структуры, точного извлечения
    words: List[Word] = field(default_factory=list)
    
    # Метаданные обработки
    metadata: Optional[OCRMetadata] = None
