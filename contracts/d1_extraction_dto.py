"""
DTO контракт: D1 (Extraction) -> D2 (Parsing)

Результат OCR обработки изображения чека.
Содержит полный текст И слова с координатами для максимального качества парсинга.

ВАЖНО: Это НАША зона свободы. Мы авторы этого контракта.
Оптимизируем для достижения 100% качества парсинга.

Решение: ADR-006 - передавать и full_text, и words[] с координатами.

ВАЛИДАЦИЯ: Pydantic гарантирует корректность данных на выходе из D1.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Dict, Any


class BoundingBox(BaseModel):
    """
    Координаты слова на изображении.
    
    Валидация:
    - x, y >= 0 (координаты не могут быть отрицательными)
    - width, height > 0 (размеры должны быть положительными)
    """
    x: int = Field(..., ge=0, description="Левый верхний угол X")
    y: int = Field(..., ge=0, description="Левый верхний угол Y")
    width: int = Field(..., gt=0, description="Ширина")
    height: int = Field(..., gt=0, description="Высота")
    
    model_config = ConfigDict(frozen=True)


class Word(BaseModel):
    """
    Отдельное слово распознанное OCR.
    
    Используется для:
    - Понимания layout (где левая колонка, где правая)
    - Разделения названия товара от цены по X-координате
    - Группировки слов в строки по Y-координате
    - Понимания качества распознавания (confidence)
    
    Валидация:
    - text не может быть пустым
    - confidence в диапазоне [0.0, 1.0]
    """
    text: str = Field(..., min_length=1, description="Текст слова")
    bounding_box: BoundingBox = Field(..., description="Координаты на изображении")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Уверенность OCR (0.0 - 1.0)")
    
    model_config = ConfigDict(frozen=True)


class OCRMetadata(BaseModel):
    """
    Метаданные OCR обработки.
    
    Валидация:
    - source_file не может быть пустым
    - image_width, image_height > 0
    - processed_at в формате ISO 8601
    - retry_info опционален (добавляется если был Feedback Loop)
    """
    source_file: str = Field(..., min_length=1, description="Имя исходного файла")
    image_width: int = Field(..., gt=0, description="Ширина изображения (px)")
    image_height: int = Field(..., gt=0, description="Высота изображения (px)")
    processed_at: str = Field(..., description="Timestamp обработки (ISO 8601)")
    preprocessing_applied: List[str] = Field(
        default_factory=list, 
        description="Что применено (grayscale, deskew, etc.)"
    )
    retry_info: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Информация о Feedback Loop retry попытках. "
            "Содержит: attempts, final_avg_confidence, final_min_confidence, "
            "strategies_used, was_retried, attempt_details"
        )
    )
    
    model_config = ConfigDict(frozen=True)
    
    @field_validator('processed_at')
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        """Базовая проверка формата ISO 8601."""
        if not v or len(v) < 10:
            raise ValueError("processed_at должен быть в формате ISO 8601")
        return v


class RawOCRResult(BaseModel):
    """
    Результат OCR обработки изображения.
    
    Содержит ДВА представления данных:
    1. full_text - для быстрых regex, поиска паттернов, определения локали
    2. words[] - для понимания layout, структуры, точного извлечения
    
    Это дает D2 максимум информации для достижения 100% качества.
    
    Примеры использования:
    
    # Быстрый поиск локали
    if "zu zahlen" in raw_ocr.full_text.lower():
        locale = "de_DE"
    
    # Точное извлечение цен (правая колонка)
    for word in raw_ocr.words:
        if word.bounding_box.x > image_width * 0.7:
            prices.append(word.text)
    
    Валидация:
    - Если есть words, должен быть и full_text (или наоборот)
    - metadata опционален, но рекомендуется
    """
    
    # Полный текст одной строкой
    # Используется для: regex, поиска паттернов, определения локали
    full_text: str = Field("", description="Полный текст чека")
    
    # Слова с координатами
    # Используется для: layout, структуры, точного извлечения
    words: List[Word] = Field(default_factory=list, description="Слова с координатами")
    
    # Метаданные обработки
    metadata: Optional[OCRMetadata] = Field(None, description="Метаданные OCR обработки")
    
    model_config = ConfigDict(frozen=True)
    
    @field_validator('full_text')
    @classmethod
    def validate_full_text(cls, v: str) -> str:
        """Убираем лишние пробелы."""
        return v.strip() if v else ""
    
    def has_content(self) -> bool:
        """Проверяет наличие контента (full_text или words)."""
        return bool(self.full_text) or bool(self.words)
    
    def get_words_in_region(
        self, 
        x_min: int = 0, 
        x_max: int = 10000, 
        y_min: int = 0, 
        y_max: int = 10000
    ) -> List[Word]:
        """
        Возвращает слова в указанной области.
        
        Полезно для:
        - Извлечения правой колонки (цены)
        - Извлечения верхней части (заголовок)
        - Группировки по строкам
        """
        return [
            word for word in self.words
            if x_min <= word.bounding_box.x <= x_max
            and y_min <= word.bounding_box.y <= y_max
        ]
    
    def get_lines_by_y(self, threshold: int = 15) -> List[List[Word]]:
        """
        Группирует слова в строки по Y-координате.
        
        Args:
            threshold: Максимальная разница Y для одной строки (px)
            
        Returns:
            Список строк (каждая строка = список слов)
        """
        if not self.words:
            return []
        
        # Сортируем по Y
        sorted_words = sorted(self.words, key=lambda w: w.bounding_box.y)
        
        lines: List[List[Word]] = []
        current_line: List[Word] = [sorted_words[0]]
        current_y = sorted_words[0].bounding_box.y
        
        for word in sorted_words[1:]:
            if abs(word.bounding_box.y - current_y) <= threshold:
                current_line.append(word)
            else:
                # Сортируем слова в строке по X
                current_line.sort(key=lambda w: w.bounding_box.x)
                lines.append(current_line)
                current_line = [word]
                current_y = word.bounding_box.y
        
        # Добавляем последнюю строку
        if current_line:
            current_line.sort(key=lambda w: w.bounding_box.x)
            lines.append(current_line)
        
        return lines
