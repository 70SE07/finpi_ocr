"""
Валидационные контракты (contracts) для D1 Pipeline (S0-S5).

Каждый контракт гарантирует:
  1. Правильный тип данных (type safety)
  2. Значения в допустимых диапазонах (data integrity)
  3. Обязательные поля (completeness)
  4. Возможность автоматического документирования (API schema)

Без этих контрактов система может передавать невалидные данные:
  - brightness = -100 (должна быть [0, 255])
  - contrast = NaN (должна быть >= 0)
  - noise = Inf (должна быть >= 0)
  - filter_plan = ["unknown_filter"] (неизвестный фильтр)

Все модели используют Pydantic v2 с Field validators.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError
from datetime import datetime


# ============================================================================
# STAGE 0: COMPRESSION
# ============================================================================

class CompressionRequest(BaseModel):
    """Входной контракт для Stage 0 (Compression)."""
    
    model_config = ConfigDict(frozen=True)
    
    file_path: str = Field(..., description="Путь к исходному JPEG файлу")
    original_width: int = Field(..., gt=0, description="Исходная ширина изображения (pixels)")
    original_height: int = Field(..., gt=0, description="Исходная высота изображения (pixels)")
    file_size_bytes: int = Field(..., gt=0, description="Размер файла в байтах")
    
    @field_validator('original_width', 'original_height')
    @classmethod
    def dimensions_reasonable(cls, v: int) -> int:
        """Размеры не должны быть экстремальными."""
        if v > 10000:
            raise ValueError(f"Размер слишком большой: {v}px (макс 10000px)")
        return v


class CompressionResponse(BaseModel):
    """Выходной контракт для Stage 0 (Compression)."""
    
    model_config = ConfigDict(frozen=True)
    
    target_width: int = Field(..., gt=0, description="Целевая ширина для resize (pixels)")
    target_height: int = Field(..., gt=0, description="Целевая высота для resize (pixels)")
    jpeg_quality: int = Field(..., ge=50, le=95, description="Качество JPEG [50-95]")
    adaptive_density: float = Field(..., ge=0, description="Плотность пикселей (pixels/byte)")
    scale_factor: float = Field(..., gt=0, le=1.0, description="Коэффициент сжатия (0-1]")
    
    @field_validator('target_width', 'target_height')
    @classmethod
    def target_dimensions_reasonable(cls, v: int) -> int:
        """Целевые размеры должны быть > 100px."""
        if v < 100:
            raise ValueError(f"Целевой размер слишком маленький: {v}px (мин 100px)")
        return v


# ============================================================================
# STAGE 1: PREPARATION
# ============================================================================

class PreparationRequest(BaseModel):
    """Входной контракт для Stage 1 (Preparation)."""
    
    model_config = ConfigDict(frozen=True)
    
    image_path: str = Field(..., description="Путь к JPEG файлу")
    target_size: Optional[tuple[int, int]] = Field(None, description="Целевой размер (width, height)")
    
    @field_validator('target_size')
    @classmethod
    def target_size_valid(cls, v: Optional[tuple[int, int]]) -> Optional[tuple[int, int]]:
        """Если задан целевой размер, он должен быть положительным."""
        if v is not None:
            if v[0] <= 0 or v[1] <= 0:
                raise ValueError(f"Размер должен быть > 0, получено: {v}")
        return v


class PreparationResponse(BaseModel):
    """Выходной контракт для Stage 1 (Preparation)."""
    
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    
    image_data: bytes = Field(..., description="Бинарные данные изображения (не сохраняются в JSON)")
    width: int = Field(..., gt=0, description="Фактическая ширина загруженного изображения")
    height: int = Field(..., gt=0, description="Фактическая высота загруженного изображения")
    channels: int = Field(..., ge=1, le=4, description="Количество каналов (1=Gray, 3=BGR, 4=BGRA)")
    image_hash: str = Field(..., description="SHA256 хэш для дебага (не для security)")


# ============================================================================
# STAGE 2: ANALYZER (Качество метрик)
# ============================================================================

class ImageMetrics(BaseModel):
    """
    Выходной контракт для Stage 2 (Analyzer).
    
    Метрики должны быть РЕАЛЬНЫМИ ЧИСЛАМИ (не NaN, не Inf).
    """
    
    model_config = ConfigDict(frozen=True)
    
    brightness: float = Field(
        ..., 
        ge=0, 
        le=255, 
        description="Средняя яркость [0-255]"
    )
    contrast: float = Field(
        ..., 
        ge=0, 
        description="Контраст (std deviation) [0-∞], обычно [0-100]"
    )
    noise: float = Field(
        ..., 
        ge=0, 
        description="Уровень шума (Laplacian variance) [0-∞], обычно [100-2000]"
    )
    blue_dominance: float = Field(
        ..., 
        ge=-100,
        le=100, 
        description="Доминирование синего канала [-100 to 100] (может быть отрицательным)"
    )
    image_width: int = Field(..., gt=0, description="Ширина изображения (для валидации координат)")
    image_height: int = Field(..., gt=0, description="Высота изображения (для валидации координат)")
    computed_at: datetime = Field(default_factory=datetime.utcnow, description="Время вычисления метрик")
    
    @field_validator('brightness', 'contrast', 'noise', 'blue_dominance')
    @classmethod
    def no_special_floats(cls, v: float) -> float:
        """Не допускаются NaN или Inf значения."""
        import math
        if math.isnan(v):
            raise ValueError(f"Значение не может быть NaN")
        if math.isinf(v):
            raise ValueError(f"Значение не может быть Inf")
        return v
    
    @field_validator('contrast', 'noise')
    @classmethod
    def reasonable_ranges(cls, v: float, info: Any) -> float:
        """Проверить разумность диапазонов (широкие границы для реальных данных)."""
        field_name = info.field_name
        
        # Для контраста: реально могут быть значения до 200+ для очень зернистых изображений
        if field_name == 'contrast' and v > 300:
            raise ValueError(f"Контраст {v} выглядит неправдоподобно высоким (макс ~300)")
        
        # Для шума (Laplacian variance): может быть до 10000+ для очень шумных изображений
        if field_name == 'noise' and v > 50000:
            raise ValueError(f"Шум {v} выглядит неправдоподобно высоким (макс ~50000)")
        
        return v


# ============================================================================
# STAGE 3: SELECTOR (Выбор фильтров)
# ============================================================================

class FilterType(str, Enum):
    """Доступные типы фильтров для Stage 4."""
    GRAYSCALE = "grayscale"           # Обязательный, всегда первый
    CLAHE = "clahe"                   # Adaptive histogram equalization (контраст)
    DENOISE = "denoise"               # Bilateral/NLM denoise (шум)
    SHARPEN = "sharpen"               # Резкость (опционально)


class QualityLevel(str, Enum):
    """Уровни качества съёмки для классификации."""
    BAD = "bad"                       # Критически плохое (макс обработка)
    LOW = "low"                       # Плохое (агрессивная обработка)
    MEDIUM = "medium"                 # Среднее (стандартная обработка)
    HIGH = "high"                     # Хорошее (минимальная обработка)


class FilterPlan(BaseModel):
    """
    Выходной контракт для Stage 3 (Selector).
    
    План фильтров, которые нужно применить в Stage 4.
    Всегда начинается с GRAYSCALE, остальные добавляются по необходимости.
    """
    
    model_config = ConfigDict(frozen=True)
    
    filters: List[FilterType] = Field(
        ..., 
        min_length=1,
        description="Список фильтров в порядке применения (первый = GRAYSCALE)"
    )
    quality_level: QualityLevel = Field(
        ..., 
        description="Классифицированный уровень качества"
    )
    reason: str = Field(
        ..., 
        description="Человеко-читаемое объяснение выбора фильтров (для логирования)"
    )
    metrics_snapshot: Dict[str, float] = Field(
        ..., 
        description="Снимок метрик на момент выбора (для дебага)"
    )
    
    @field_validator('filters')
    @classmethod
    def first_filter_is_grayscale(cls, v: List[FilterType]) -> List[FilterType]:
        """Первый фильтр ДОЛЖЕН быть GRAYSCALE."""
        if not v or v[0] != FilterType.GRAYSCALE:
            raise ValueError("Первый фильтр должен быть GRAYSCALE")
        return v
    
    @field_validator('filters')
    @classmethod
    def no_duplicate_filters(cls, v: List[FilterType]) -> List[FilterType]:
        """Не должно быть дублей фильтров."""
        if len(v) != len(set(v)):
            raise ValueError(f"Найдены дублирующиеся фильтры: {v}")
        return v


# ============================================================================
# STAGE 4: EXECUTOR (Применение фильтров)
# ============================================================================

class ExecutorRequest(BaseModel):
    """Входной контракт для Stage 4 (Executor)."""
    
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    
    image_data: bytes = Field(..., description="BGR изображение (не сохраняется в JSON)")
    image_width: int = Field(..., gt=0, description="Ширина изображения")
    image_height: int = Field(..., gt=0, description="Высота изображения")
    filter_plan: FilterPlan = Field(..., description="План фильтров из Stage 3")


class ExecutorResponse(BaseModel):
    """Выходной контракт для Stage 4 (Executor)."""
    
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    
    image_data: bytes = Field(..., description="Обработанное Grayscale изображение")
    width: int = Field(..., gt=0, description="Ширина результата")
    height: int = Field(..., gt=0, description="Высота результата")
    applied_filters: List[FilterType] = Field(..., description="Какие фильтры были применены")
    processing_time_ms: float = Field(..., ge=0, description="Время обработки в миллисекундах")


# ============================================================================
# STAGE 5: ENCODER (Кодирование в JPEG)
# ============================================================================

class EncoderRequest(BaseModel):
    """Входной контракт для Stage 5 (Encoder)."""
    
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    
    image_data: bytes = Field(..., description="Grayscale изображение")
    width: int = Field(..., gt=0, description="Ширина изображения")
    height: int = Field(..., gt=0, description="Высота изображения")
    quality: int = Field(..., ge=50, le=95, description="Качество JPEG [50-95]")


class EncoderResponse(BaseModel):
    """Выходной контракт для Stage 5 (Encoder)."""
    
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    
    jpeg_bytes: bytes = Field(..., description="Закодированный JPEG")
    jpeg_quality: int = Field(..., ge=50, le=95, description="Использованное качество")
    original_size_kb: float = Field(..., ge=0, description="Размер до кодирования (KB)")
    encoded_size_kb: float = Field(..., ge=0, description="Размер после кодирования (KB)")
    compression_ratio: float = Field(..., gt=0, description="Ratio original/encoded")


# ============================================================================
# GOOGLE VISION API INTEGRATION
# ============================================================================

class GoogleVisionVertice(BaseModel):
    """Single vertice из Google Vision response."""
    
    model_config = ConfigDict(frozen=True)
    
    x: int = Field(..., ge=0, description="X координата пикселя")
    y: int = Field(..., ge=0, description="Y координата пикселя")


class GoogleVisionBoundingBox(BaseModel):
    """Bounding box из Google Vision response."""
    
    model_config = ConfigDict(frozen=True)
    
    vertices: List[GoogleVisionVertice] = Field(
        ..., 
        min_length=4, 
        max_length=4,
        description="4 вершины прямоугольника (всегда 4)"
    )
    
    @field_validator('vertices')
    @classmethod
    def all_coordinates_positive(cls, v: List[GoogleVisionVertice]) -> List[GoogleVisionVertice]:
        """Все координаты должны быть неотрицательными."""
        for vertice in v:
            if vertice.x < 0 or vertice.y < 0:
                raise ValueError(f"Отрицательная координата: ({vertice.x}, {vertice.y})")
        return v


class GoogleVisionWord(BaseModel):
    """Word из Google Vision response (из текущего RawOCRResult)."""
    
    model_config = ConfigDict(frozen=True)
    
    text: str = Field(..., min_length=1, description="Текст слова")
    bounding_box: GoogleVisionBoundingBox = Field(..., description="Bounding box слова")
    confidence: float = Field(..., ge=0, le=1, description="Confidence [0-1]")


class GoogleVisionPageResponse(BaseModel):
    """Полный response от Google Vision API для одной страницы."""
    
    model_config = ConfigDict(frozen=True)
    
    full_text: str = Field(..., description="Полный распознанный текст")
    words: List[GoogleVisionWord] = Field(..., description="Слова с координатами")
    confidence: float = Field(..., ge=0, le=1, description="Общая confidence")
    
    @field_validator('full_text')
    @classmethod
    def full_text_not_empty(cls, v: str) -> str:
        """Хотя бы что-то должно быть распознано."""
        if not v or not v.strip():
            raise ValueError("Google Vision вернула пустой текст")
        return v.strip()
    
    @field_validator('words')
    @classmethod
    def words_not_empty(cls, v: List[GoogleVisionWord]) -> List[GoogleVisionWord]:
        """Должно быть хотя бы одно слово."""
        if not v:
            raise ValueError("Google Vision вернула пустой список слов")
        return v


class GoogleVisionValidatedResponse(BaseModel):
    """
    Валидированный response от Google Vision с дополнительными проверками.
    
    Эта модель расширяет базовую GoogleVisionPageResponse с проверками
    на соответствие размерам изображения.
    """
    
    model_config = ConfigDict(frozen=True)
    
    full_text: str = Field(..., description="Полный распознанный текст")
    words: List[GoogleVisionWord] = Field(..., description="Слова с координатами")
    confidence: float = Field(..., ge=0, le=1, description="Общая confidence")
    image_width: int = Field(..., gt=0, description="Ширина исходного изображения")
    image_height: int = Field(..., gt=0, description="Высота исходного изображения")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('words')
    @classmethod
    def coordinates_within_bounds(cls, v: List[GoogleVisionWord], info: Any) -> List[GoogleVisionWord]:
        """Координаты слов должны быть в пределах размеров изображения."""
        if 'image_width' not in info.data or 'image_height' not in info.data:
            # При валидации без контекста этот check пропускается
            return v
        
        image_width = info.data.get('image_width', 0)
        image_height = info.data.get('image_height', 0)
        
        if image_width <= 0 or image_height <= 0:
            return v
        
        for word in v:
            for vertice in word.bounding_box.vertices:
                if vertice.x > image_width or vertice.y > image_height:
                    raise ValueError(
                        f"Координата слова '{word.text}' вне границ: "
                        f"({vertice.x}, {vertice.y}) > ({image_width}, {image_height})"
                    )
        
        return v


# ============================================================================
# PIPELINE STATE & CONTEXT
# ============================================================================

class PipelineStageMetadata(BaseModel):
    """Метаданные о выполнении каждой стадии."""
    
    stage_name: str = Field(..., description="Имя стадии (S0, S1, ..., S5)")
    execution_time_ms: float = Field(..., ge=0, description="Время выполнения")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., description="success, warning, error")
    message: Optional[str] = Field(None, description="Опциональное сообщение")


class D1ExtractionPipelineState(BaseModel):
    """
    Полное состояние D1 pipeline для отладки и аудита.
    
    Содержит снимки данных на каждом этапе для возможности
    откатывания и анализа проблем.
    """
    
    model_config = ConfigDict(frozen=False)  # Собирается постепенно
    
    pipeline_id: str = Field(..., description="Уникальный ID для отслеживания")
    source_file: str = Field(..., description="Исходный файл изображения")
    
    # Промежуточные результаты
    compression: Optional[CompressionResponse] = Field(None)
    preparation: Optional[PreparationResponse] = Field(None)
    metrics: Optional[ImageMetrics] = Field(None)
    filter_plan: Optional[FilterPlan] = Field(None)
    execution: Optional[ExecutorResponse] = Field(None)
    encoding: Optional[EncoderResponse] = Field(None)
    
    # Финальный результат OCR
    ocr_result: Optional[GoogleVisionValidatedResponse] = Field(None)
    
    # Метаданные
    stages_metadata: List[PipelineStageMetadata] = Field(default_factory=list)
    total_duration_ms: float = Field(default=0.0)
    success: bool = Field(default=False)


# ============================================================================
# ERRORS & DIAGNOSTICS
# ============================================================================

class ContractValidationError(Exception):
    """Exception для нарушения контрактов (используется вместо Pydantic ValidationError)."""
    
    def __init__(self, stage_name: str, contract_name: str, errors: Union[List[Dict[str, Any]], List[Any]]) -> None:
        self.stage_name = stage_name
        self.contract_name = contract_name
        self.errors = errors
        
        error_messages = []
        for err in errors:
            if isinstance(err, dict):
                # Pydantic v1 style dict
                loc = err.get('loc', [])[0] if err.get('loc') else 'unknown'
                err_type = err.get('type', 'unknown')
                msg = err.get('msg', 'unknown error')
                error_messages.append(f"  {loc} ({err_type}): {msg}")
            else:
                # Pydantic v2 ErrorDetails or other
                error_messages.append(f"  {str(err)}")
        
        message = (
            f"❌ Contract violation in {stage_name} ({contract_name}):\n"
            + "\n".join(error_messages)
        )
        super().__init__(message)
