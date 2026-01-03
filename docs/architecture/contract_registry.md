# Реестр Контрактов (Contract Registry)

Данный документ фиксирует нерушимые договорённости между операциями пайплайна. Каждая операция обязана поставлять результат, соответствующий своему Контракту.

## Философия

**Stage = SRP = ЦКП.** Каждый контракт описывает ЦКП (Ценный Конечный Продукт) операции.

Подробнее: [PROJECT_VISION.md](../PROJECT_VISION.md#философия-stages-в-пайплайне) | Термины: [GLOSSARY.md](../GLOSSARY.md)

---

## 1. Extraction Домен: Контракты Pre-OCR Pipeline

### 1.1. ImageMetrics Contract (Stage 2)

**Контракт:** `src/domain/contracts.py::ImageMetrics`

**ЦКП:** Метрики качества изображения (с гарантиями валидности)

```python
class ImageMetrics(BaseModel):
    brightness: float      # [0-255] - средняя яркость
    contrast: float         # [0-∞] - RMS контраст
    noise: float            # [0-∞] - шум (Laplacian variance)
    blue_dominance: float   # [-100, 100] - доминирование синего канала
    image_width: int
    image_height: int
```

**Валидация (гарантии):**
- ✅ Brightness в диапазоне [0, 255]
- ✅ Contrast >= 0
- ✅ Noise >= 0
- ✅ NO NaN или Inf значений (валидатор)

**Где используется:** Stage 2 (Analyzer) → вычисляет метрики из сжатого изображения

---

### 1.2. QualityLevel Enum

**Контракт:** `src/domain/contracts.py::QualityLevel`

**ЦКП:** Уровни качества съёмки

```python
class QualityLevel(str, Enum):
    BAD = "bad"          # Критически плохое (максимум обработки)
    LOW = "low"          # Плохое (агрессивная обработка)
    MEDIUM = "medium"     # Среднее (стандартная обработка)
    HIGH = "high"        # Хорошее (минимум обработки)
```

**Где используется:**
- Stage 2 (QualityClassifier) → классифицирует качество
- Stage 3 (Selector) → выбирает пороги фильтров по уровню качества

**Классификация (QualityClassifier):**
```python
# BAD: критически плохое
if brightness < 40 or brightness > 245 or contrast < 5 or noise > 5000:
    return QualityLevel.BAD

# HIGH: хорошее
if 80 <= brightness <= 210 and contrast >= 40 and noise <= 1500:
    return QualityLevel.HIGH

# MEDIUM: среднее
if 70 <= brightness <= 225 and contrast >= 15 and noise <= 2500:
    return QualityLevel.MEDIUM

# LOW: плохое (по умолчанию)
return QualityLevel.LOW
```

---

### 1.3. FilterType Enum

**Контракт:** `src/domain/contracts.py::FilterType`

**ЦКП:** Доступные типы фильтров для Stage 4

```python
class FilterType(str, Enum):
    GRAYSCALE = "grayscale"           # Обязательный, всегда первый
    CLAHE = "clahe"                   # Adaptive histogram equalization (контраст)
    DENOISE = "denoise"               # Bilateral/NLM denoise (шум)
    SHARPEN = "sharpen"               # Резкость (опционально для aggressive)
```

**Где используется:** Stage 4 (Executor) → применяет фильтры к изображению

---

### 1.4. FilterPlan Contract (Stage 3)

**Контракт:** `src/domain/contracts.py::FilterPlan`

**ЦКП:** План фильтров для применения в Stage 4

```python
class FilterPlan(BaseModel):
    filters: List[FilterType]  # Список фильтров в порядке применения
    quality_level: QualityLevel  # Классифицированный уровень качества
    reason: str  # Человеко-читаемое объяснение выбора
    metrics_snapshot: Dict[str, float]  # Снимок метрик на момент выбора
```

**Валидация (гарантии):**
- ✅ Фильтры не пустые (min_length=1)
- ✅ Первый фильтр ВСЕГДА GRAYSCALE
- ✅ Нет дубликатов фильтров

**Где определяется:** Stage 3 (Selector)

---

## 2. Feedback Loop Contract (D1 Pipeline)

### 2.1. 3 Стратегии Retry

**ЦКП:** Адаптивный retry с анализом confidence

| Стратегия | Когда используется | Фильтры | JPEG качество |
|-----------|------------------|----------|---------------|
| Adaptive (по умолчанию) | Первая попытка | Quality-based | 85% |
| Aggressive (retry #1) | Если confidence низкий | Форсировать BAD quality | 95% |
| Minimal (retry #2) | Если все попытки исчерпаны | Только GRAYSCALE | PNG |

**Пороги конфигурации:** `config/settings.py`
```python
ENABLE_FEEDBACK_LOOP = True
MAX_RETRIES = 2
CONFIDENCE_EXCELLENT_THRESHOLD = 0.95  # Принять сразу
CONFIDENCE_ACCEPTABLE_THRESHOLD = 0.90  # Принять
CONFIDENCE_RETRY_THRESHOLD = 0.85      # Retry
CONFIDENCE_MIN_WORD_THRESHOLD = 0.70     # Минимальный confidence для слова
CONFIDENCE_MAX_LOW_RATIO = 0.20          # Макс. доля слов с низким confidence
```

**Логика retry (ExtractionPipeline):**
```python
# Попытка 1: Adaptive
result = process_image_with_retry(strategy={"name": "adaptive"})
avg_conf = calculate_average_confidence(result.words)
min_conf = calculate_min_confidence(result.words)

if avg_conf < CONFIDENCE_RETRY_THRESHOLD:
    # Попытка 2: Aggressive
    result = process_image_with_retry(strategy={"name": "aggressive"})
    
if not result_acceptable:
    # Попытка 3: Minimal
    result = process_image_with_retry(strategy={"name": "minimal"})
```

---

### 2.2. Quality-Based Filter Selection

**КРИТИЧЕСКИ ВАЖНО: БЕЗ МАГАЗИННОЙ ЛОГИКИ!**

Фильтры выбираются ТОЛЬКО на основе качества съёмки, НЕ магазина/локали/камеры.

**Пороги для каждого уровня качества:**

| Quality | Noise Threshold | CLAHE Threshold | Фильтры |
|---------|-----------------|-----------------|----------|
| BAD | <900 | <40 | grayscale, clahe, denoise |
| LOW | <1100 | <50 | grayscale, clahe, denoise |
| MEDIUM | <1300 | <60 | grayscale, clahe, denoise |
| HIGH | <1500 | <80 | grayscale |

**Где определены:** `config/settings.py`
- Пороги классификации: `BRIGHTNESS_BAD_MIN/MAX`, `CONTRAST_BAD_MAX`, `NOISE_BAD_MIN`
- Пороги фильтров: в `QualityBasedFilterSelector.thresholds[quality]`

**Логика выбора (QualityBasedFilterSelector):**
```python
# Всегда добавляем grayscale
filters = [FilterType.GRAYSCALE]

# Получаем пороги для текущего уровня качества
thresholds = QualityBasedFilterSelector.thresholds[quality]

# CLAHE нужен когда контраст ниже порога
if metrics.contrast < thresholds["clahe_contrast_threshold"]:
    filters.append(FilterType.CLAHE)

# Denoise нужен когда шум выше порога
if metrics.noise > thresholds["denoise_noise_threshold"]:
    filters.append(FilterType.DENOISE)

# Формируем план
plan = FilterPlan(
    filters=filters,
    quality_level=quality,
    reason="Плохое качество + низкий контраст + высокий шум",
    metrics_snapshot={...}
)
```

**Почему НЕ магазинная логика:**
- ✅ Шум = шум, независимо от магазина (Aldi, Rewe, DM, Edeka)
- ✅ Яркость = яркость, независимо от локали (de_DE, pl_PL, th_TH)
- ✅ Контраст = контраст, независимо от камеры (iPhone, Pixel, Samsung)
- ✅ Масштабируется на 100+ магазинов автоматически
- ✅ НЕ нужно писать `if shop == "Aldi"` для каждого магазина

---

## 3. Контракт между доменами (D1 → D2)

**Контракт:** `contracts/d1_extraction_dto.py::RawOCRResult`

**ЦКП:** Результат OCR (полный текст + слова с координатами)

```python
class RawOCRResult(BaseModel):
    full_text: str                      # Полный текст чека
    words: List[Word]                   # Слова с координатами
    metadata: OCRMetadata                # Метаданные OCR
    
    class Word(BaseModel):
        text: str                         # Текст слова
        bounding_box: BoundingBox           # Координаты (x, y, width, height)
        confidence: float                   # Уверенность OCR [0.0-1.0]
    
    class BoundingBox(BaseModel):
        x: int      # Левый верхний угол X
        y: int      # Левый верхний угол Y
        width: int  # Ширина
        height: int  # Высота
    
    class OCRMetadata(BaseModel):
        source_file: str                    # Имя исходного файла
        image_width: int                    # Ширина изображения
        image_height: int                   # Высота изображения
        processed_at: str                   # Время обработки (ISO 8601)
        preprocessing_applied: List[str]     # Применённые фильтры
        retry_info: Optional[Dict]          # Информация о retry попытках
```

**Ключевые особенности RawOCRResult:**
- ✅ `words[]` - список слов с координатами (позволяет понимать layout)
- ✅ `full_text` - полный текст чека (гарантия 100% качества OCR)
- ✅ `confidence` для каждого слова (позволяет анализировать качество OCR)
- ✅ `preprocessing_applied` - какие фильтры были применены
- ✅ `retry_info` - информация о Feedback Loop попытках

**Почему `words[]` вместо `blocks[]`:**
Слова с координатами позволяют D2 группировать их в строки по Y-координате и понимать layout (колонки, отступы).

---

## Итоговая таблица контрактов

| Контракт | Модуль | Стадия | ЦКП |
|----------|---------|--------|-----|
| `ImageMetrics` | `src/domain/contracts.py` | Stage 2 (Analyzer) | Метрики качества |
| `QualityLevel` | `src/domain/contracts.py` | Stage 2/3 | Уровни качества |
| `FilterType` | `src/domain/contracts.py` | Stage 4 (Executor) | Типы фильтров |
| `FilterPlan` | `src/domain/contracts.py` | Stage 3 (Selector) | План фильтров |
| `RawOCRResult` | `contracts/d1_extraction_dto.py` | D1→D2 | Результат OCR |

---

## Принципы разработки контрактов

### 1. Валидация через Pydantic
- Все контракты используют `BaseModel` из Pydantic
- Автоматическая валидация типов
- Автоматическая документация

### 2. Гарантии качества
- NO NaN или Inf значений (валидаторы)
- Диапазоны значений (brightness [0-255], confidence [0-1])
- Обязательные поля (min_length=1)

### 3. Хороший дизайн (Good Design)
- Человеко-читаемые названия (`brightness`, `contrast`, `noise`)
- Описания полей (`description`)
- Логирование всех действий

### 4. Контрактная безопасность
- Невозможно нарушить контракт (валидация на входе)
- Стабильная структура данных между модулями
- Лёгкая замена реализаций без изменения архитектуры
