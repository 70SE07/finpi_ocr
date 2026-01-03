# Архитектура проекта Finpi OCR

## Обзор

Finpi OCR - это система для оцифровки чеков из 100+ стран с использованием Google Vision OCR и языковой модели.

**Ключевые принципы:**
- Domain-Driven Design
- Quality-Based Filter Selection (БЕЗ МАГАЗИННОЙ ЛОГИКИ!)
- Адаптивный Feedback Loop
- Контрактная безопасность (Pydantic)

## Три домена системы

```
[Изображение чека] → Extraction домен → [RawOCRResult] → Parsing домен → [Structured Result]
                  (независимый)      (контракт)        (независимый)
```

## Extraction домен (src/extraction/)

### Ответственность
- **ЦКП:** Оцифрованный текст чека без потерь
- **Выход:** `RawOCRResult` (контракт D1→D2)

### 6-Stage Adaptive Preprocessing Pipeline

**Stage 0: Compression (адаптивное сжатие)**
- Адаптивное вычисление целевого размера БЕЗ загрузки изображения
- Оптимизация размера/веса для быстрой передачи в Google Vision API
- Контракт: `CompressionRequest/Response`

**Stage 1: Preparation (загрузка + resize)**
- Загрузка изображения сразу в целевом размере
- Оптимизация использования памяти
- Контракт: `PreparationRequest/Response`

**Stage 2: Analyzer (анализ метрик качества)**
- Вычисление метрик из сжатого изображения:
  - `brightness` [0-255] - средняя яркость
  - `contrast` [0-∞] - RMS контраст
  - `noise` [0-∞] - шум/резкость (Laplacian variance)
  - `blue_dominance` [-100, 100] - доминирование синего канала
- Контракт: `ImageMetrics` (валидация no NaN/Inf)

**Stage 3: Selector (выбор фильтров по качеству)**
- **КРИТИЧЕСКИ ВАЖНО:** БЕЗ МАГАЗИННОЙ ЛОГИКИ!
- Классификация качества съёмки: BAD/LOW/MEDIUM/HIGH
- Выбор фильтров на основе ТОЛЬКО качества, не магазина/локали/камеры
- Фильтры: grayscale, CLAHE, denoise
- Контракт: `FilterPlan` (валидация порядка: GRAYSCALE всегда первый)

**Stage 4: Executor (применение фильтров)**
- Применение выбранных фильтров к изображению
- Grayscale (всегда), затем опционально CLAHE и denoise
- Контракт: `ExecutorRequest/Response`

**Stage 5: Encoder (кодирование в JPEG)**
- Кодирование обработанного изображения в JPEG для отправки в Google Vision API
- Адаптивное качество JPEG в зависимости от стратегии
- Контракт: `EncoderRequest/Response`

### Quality-Based Filter Selection

**Почему НЕ магазинная логика:**
- Шум = шум, независимо от магазина
- Яркость = яркость, независимо от локали
- Контраст = контраст, независимо от камеры
- Универсальное решение для 100+ магазинов

**Пороги для каждого уровня качества:**

| Quality | Noise Threshold | CLAHE Threshold | Фильтры |
|---------|-----------------|------------------|----------|
| BAD | <900 | <40 | grayscale, clahe, denoise |
| LOW | <1100 | <50 | grayscale, clahe, denoise |
| MEDIUM | <1300 | <60 | grayscale, clahe, denoise |
| HIGH | <1500 | <80 | grayscale |

**Где определены:** `config/settings.py`
- `NOISE_BAD_MIN`, `NOISE_MEDIUM_MAX`, `NOISE_HIGH_MAX`
- `CONTRAST_BAD_MAX`, `CONTRAST_MEDIUM_MIN`, `CONTRAST_HIGH_MIN`
- `CLAHE_CONTRAST_THRESHOLD` (в QualityBasedFilterSelector для каждого качества)

### Feedback Loop (адаптивный retry)

**3 стратегии:**

1. **Adaptive (по умолчанию)**
   - Quality-based выбор фильтров
   - Если confidence низкий → retry с другой стратегией

2. **Aggressive (retry #1)**
   - Форсировать BAD качество
   - Применять максимум фильтров: grayscale, clahe, denoise, sharpen
   - Повышать JPEG качество до 95%

3. **Minimal (retry #2)**
   - Форсировать HIGH качество
   - Только grayscale (минимум обработки)
   - PNG без сжатия (качество 100%)

**Логика retry:**
- Пороги конфигурации в `config/settings.py`
- `CONFIDENCE_EXCELLENT_THRESHOLD = 0.95`
- `CONFIDENCE_ACCEPTABLE_THRESHOLD = 0.90`
- `CONFIDENCE_RETRY_THRESHOLD = 0.85`
- `CONFIDENCE_MIN_WORD_THRESHOLD = 0.70`
- `CONFIDENCE_MAX_LOW_RATIO = 0.20`
- `MAX_RETRIES = 2`

### Google Vision OCR Integration

- Провайдер: `GoogleVisionOCR` (инфраструктура)
- Интерфейс: `IOCRProvider`
- Контракт: `RawOCRResult` (контракт D1→D2)
- Вход: байты обработанного изображения
- Выход: `full_text` + `words[]` с координатами

## Parsing домен (src/parsing/)

### Ответственность
- **ЦКП:** Структурированные данные чека
- **Вход:** `RawOCRResult` (контракт от Extraction)
- **Выход:** `Structured Result`

### Конфигурация локалей (src/parsing/locales/)

Конфигурации локалей в формате YAML для 100+ стран:
- `de_DE/` - Германия (EUR, German)
- `pl_PL/` - Польша (PLN, Polish)
- `[98 других локалей]`

Структура конфигурации:
- `locale:` - код, название, язык, регион
- `currency:` - код, символ, разделители, формат
- `date_formats:` - форматы даты
- `patterns:` - ключевые слова, бренды, исключения

## Контракты между доменами

### D1→D2 (Extraction → Parsing)

**Контракт:** `contracts/d1_extraction_dto.py`

**RawOCRResult:**
```json
{
  "full_text": "Полный текст чека...",
  "words": [
    {
      "text": "REWE",
      "bounding_box": {"x": 100, "y": 50, "width": 80, "height": 20},
      "confidence": 0.98
    },
    {
      "text": "Milch",
      "bounding_box": {"x": 50, "y": 200, "width": 60, "height": 18},
      "confidence": 0.95
    }
  ],
  "metadata": {
    "source_file": "IMG_1292",
    "image_width": 800,
    "image_height": 1200,
    "processed_at": "2024-12-31T10:30:00",
    "preprocessing_applied": ["grayscale", "denoise"]
  }
}
```

**Ключевые особенности:**
- `words[]` - список слов с координатами
- `full_text` - полный текст чека (гарантия 100% качества OCR)
- Валидация через Pydantic контракты
- Метаданные для дебага и анализа

## Структура проекта

```
Finpi_OCR/
├── config/                       # Настройки
│   ├── settings.py              # Параметры системы
│   └── google_credentials.json   # Google Cloud credentials (НЕ в git!)
│
├── contracts/                    # Контракты между доменами (Pydantic)
│   ├── d1_extraction_dto.py    # D1→D2: RawOCRResult (words + full_text)
│   ├── d2_parsing_dto.py       # D2→D3: RawReceiptDTO
│   └── d3_categorization_dto.py # D3→Orchestrator: ParseResultDTO
│
├── data/                         # Данные
│   ├── input/                   # Входные изображения чеков
│   └── output/                  # Результаты обработки
│       └── raw_ocr/            # Сырые результаты OCR
│
├── docs/                         # Документация
│   ├── architecture/             # Архитектурные решения
│   │   ├── architecture_overview.md  # Обзор архитектуры (этот файл)
│   │   ├── contract_registry.md      # Реестр контрактов модулей
│   │   └── decisions/              # Архитектурные решения (ADR)
│   ├── locales/                  # Конфигурации локалей
│   ├── ground_truth/             # Ground truth данные для тестов
│   └── ocr_quality/             # Метрики качества OCR
│
├── src/                          # Исходный код
│   ├── domain/                  # Контракты доменов
│   │   └── contracts.py        # Все контракты (ImageMetrics, FilterPlan, etc.)
│   │
│   ├── extraction/               # Домен Extraction (независимый)
│   │   ├── domain/              # Интерфейсы и исключения
│   │   ├── application/          # Factory + Pipeline
│   │   ├── infrastructure/       # Адаптеры и реализации
│   │   │   └── ocr/            # Google Vision OCR
│   │   └── pre_ocr/            # 6-stage preprocessing pipeline
│   │       ├── s0_compression/   # Stage 0: Compression
│   │       ├── s1_preparation/   # Stage 1: Preparation
│   │       ├── s2_analyzer/      # Stage 2: Analyzer
│   │       │   └── quality_classifier.py  # Классификация качества
│   │       ├── s3_selector/      # Stage 3: Selector
│   │       │   └── quality_based_filter_selector.py  # Quality-based выбор фильтров
│   │       ├── s4_executor/      # Stage 4: Executor
│   │       └── s5_encoder/       # Stage 5: Encoder
│   │
│   ├── parsing/                  # Домен Parsing (независимый)
│   │   ├── domain/              # Интерфейсы и исключения
│   │   ├── application/          # Factory + Pipeline
│   │   ├── infrastructure/       # Адаптеры и реализации
│   │   ├── locales/             # Конфигурации 100+ стран
│   │   ├── metadata/            # Экстракторы метаданных
│   │   ├── layout/              # Обработка layout
│   │   └── extraction/           # Семантическое извлечение товаров
│   │
│   └── infrastructure/           # Общая инфраструктура
│
├── scripts/                      # Точки входа
│   ├── run_pipeline.py          # Полный пайплайн (Extraction + Parsing)
│   ├── extract_raw_ocr.py       # Extraction домен
│   └── parse_receipt.py         # Parsing домен
│
└── requirements.txt             # Зависимости
```

## Принципы разработки

### 1. Systemic-First Principle
- Решать проблемы на архитектурном уровне
- Использовать абстракции (`locales/`) вместо локальных фиксов
- Решения масштабируются на 100+ стран

### 2. No Pivot Rule
- Google Vision OCR — основная технология
- Оптимизация внутри текущего стека (preprocessing)
- Не менять технологию без крайней необходимости

### 3. Independent Domains
- Extraction и Parsing развиваются независимо
- Контракт между доменами стабилен
- Лёгкая замена реализаций через адаптеры

## Конфигурация Extraction

Система использует динамический подбор параметров. Значения по умолчанию:

| Параметр | Default | Стратегия при сбоe |
|----------|---------|-------------------|
| MAX_IMAGE_SIZE | 2200px | Уменьшение до 1800px при OOM |
| JPEG_QUALITY | 85% | Повышение до 100% (PNG) при низком Confidence |

## Масштабирование на 100+ локалей

### Текущее состояние
- ✅ Независимые домены (Extraction, Parsing)
- ✅ Контракт между доменами (RawOCRResult)
- ✅ Интерфейсы и адаптеры
- ✅ Система локалей через YAML
- ✅ Чистый код (без `sys.path` манипуляций в файлах внутри `src/`)

### Следующие шаги
1. Валидация YAML конфигураций локалей через Pydantic
2. Фоллбэк-локаль для неопределённых случаев
3. Централизованный реестр локалей
4. Шифрование конфигураций локалей
5. Мониторинг и логирование
6. Контракт для Parsing (Structured Result)
