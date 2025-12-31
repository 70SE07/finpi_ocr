# Архитектура проекта Finpi OCR

## Обзор

Finpi OCR - тренировочный стенд для экспериментов с Google Vision OCR и обработкой чеков из 100+ стран.

## Принципы проектирования

1. **Независимые домены (Domain-Driven Design)**
   - Extraction домен: preprocessing + OCR
   - Parsing домен: layout, locale, metadata, semantic extraction
   - Домены изолированы и могут развиваться независимо

2. **Контракт между доменами**
   - Stable contract через `contracts/raw_ocr_schema.py`
   - Extraction → Parsing через `RawOCRResult`
   - Parsing → клиент (контракт в разработке)

3. **Интерфейсы и адаптеры**
   - Каждый домен имеет свои интерфейсы (абстрактные классы)
   - Адаптеры для существующих компонентов
   - Легкая замена реализаций без изменения архитектуры

4. **Чистый код**
   - Нет манипуляций с `sys.path` в файлах внутри `src/`
   - Корень проекта добавляется один раз в `src/__init__.py`
   - Структурированные исключения для каждого домена

## Структура проекта

```
Finpi_OCR/
├── config/                     # Конфигурация
│   ├── settings.py            # Настройки системы
│   └── google_credentials.json # Google Cloud credentials
│
├── contracts/                 # Контракты между доменами
│   └── raw_ocr_schema.py     # RawOCRResult (Extraction → Parsing)
│
├── data/                      # Данные
│   ├── input/                 # Входные изображения чеков
│   └── output/                # Результаты обработки
│       └── raw_ocr/          # Сырые результаты OCR
│
├── docs/                      # Документация
│   ├── architecture/           # Архитектурные решения
│   │   ├── contract_registry.md      # Реестр контрактов модулей
│   │   └── architecture_overview.md  # Обзор архитектуры (этот файл)
│   └── hypotheses/            # Гипотезы и эксперименты
│
├── src/                       # Исходный код
│   ├── __init__.py           # Настройка sys.path
│   │
│   ├── extraction/            # Домен Extraction (независимый)
│   │   ├── domain/           # Бизнес-логика и интерфейсы
│   │   │   ├── interfaces.py         # IOCRProvider, IImagePreprocessor, IExtractionPipeline
│   │   │   └── exceptions.py         # ExtractionError, ImageProcessingError, OCRProcessingError
│   │   │
│   │   ├── application/      # Оркестрация use cases
│   │   │   ├── factory.py            # ExtractionComponentFactory
│   │   │   └── extraction_pipeline.py # ExtractionPipeline
│   │   │
│   │   ├── infrastructure/    # Реализации и адаптеры
│   │   │   ├── adapters/
│   │   │   │   ├── google_vision_adapter.py       # GoogleVisionOCRAdapter
│   │   │   │   └── image_preprocessor_adapter.py  # ImagePreprocessorAdapter
│   │   │   └── file_manager.py       # ExtractionFileManager
│   │   │
│   │   ├── ocr/              # OCR компоненты
│   │   │   └── google_vision_ocr.py  # Google Vision API интеграция
│   │   │
│   │   └── pre_ocr/         # Preprocessing
│   │       ├── preprocessor.py         # ImagePreprocessor
│   │       └── elements/
│   │           ├── image_compressor.py # Сжатие изображений
│   │           └── grayscale.py        # Конвертация в ч/б
│   │
│   ├── parsing/              # Домен Parsing (независимый)
│   │   ├── domain/           # Бизнес-логика и интерфейсы
│   │   │   ├── interfaces.py         # IReceiptParser, ILayoutProcessor, ILocaleDetector, IMetadataExtractor, ISemanticExtractor
│   │   │   └── exceptions.py         # ParsingError, LayoutProcessingError, MetadataExtractionError
│   │   │
│   │   ├── application/      # Оркестрация use cases
│   │   │   ├── factory.py            # ParsingComponentFactory
│   │   │   ├── receipt_parser.py     # ReceiptParser
│   │   │   └── parsing_pipeline.py  # ParsingPipeline
│   │   │
│   │   ├── infrastructure/    # Реализации и адаптеры
│   │   │   ├── adapters/
│   │   │   │   ├── layout_processor_adapter.py    # LayoutProcessorAdapter
│   │   │   │   ├── locale_detector_adapter.py     # LocaleDetectorAdapter
│   │   │   │   ├── metadata_extractor_adapter.py  # MetadataExtractorAdapter
│   │   │   │   └── semantic_extractor_adapter.py  # SemanticExtractorAdapter
│   │   │   └── file_manager.py       # ParsingFileManager
│   │   │
│   │   ├── locales/          # Конфигурации локалей (100+ стран)
│   │   │   ├── de_DE/                # Германия
│   │   │   ├── pl_PL/                # Польша
│   │   │   ├── locale_config.py       # LocaleConfig DTO
│   │   │   ├── locale_config_loader.py # Загрузчик YAML конфигураций
│   │   │   └── locale_detector.py    # Детектор локали
│   │   │
│   │   ├── metadata/         # Экстракторы метаданных
│   │   │   ├── metadata_extractor.py # Оркестратор метаданных
│   │   │   ├── store_detector.py      # Детектор магазина
│   │   │   ├── address_extractor.py   # Экстрактор адреса
│   │   │   ├── date_extractor.py     # Экстрактор даты
│   │   │   ├── total_extractor.py     # Экстрактор итоговой суммы
│   │   │   └── requisites_extractor.py # Экстрактор реквизитов
│   │   │
│   │   ├── layout/           # Обработка layout
│   │   │   └── layout_processor.py    # LayoutProcessor
│   │   │
│   │   ├── extraction/       # Семантическое извлечение
│   │   │   ├── semantic_extractor.py   # SemanticExtractor
│   │   │   ├── line_classifier.py     # Классификатор строк
│   │   │   ├── price_parser.py        # Парсер цен
│   │   │   ├── quantity_parser.py     # Парсер количества
│   │   │   └── [другие экстракторы]
│   │   │
│   │   └── old_project/     # Устаревший код (не используется)
│   │       └── address_fix.py
│   │
│   └── infrastructure/       # Общая инфраструктура
│       └── adapters/
│
├── scripts/                  # Точки входа
│   ├── run_pipeline.py      # Полный пайплайн (Extraction + Parsing)
│   ├── extract_raw_ocr.py   # Extraction домен
│   └── parse_receipt.py     # Parsing домен
│
└── requirements.txt          # Зависимости
```

## Домен Extraction

### Ответственность
- Preprocessing изображений (deskew, rotation, grayscale, compression)
- OCR распознавание текста
- Сохранение сырых результатов в формате `RawOCRResult`

### Интерфейсы
- `IOCRProvider` - интерфейс для провайдеров OCR
- `IImagePreprocessor` - интерфейс для препроцессоров изображений
- `IExtractionPipeline` - интерфейс для пайплайна extraction

### Использование

```python
from src.extraction.application.factory import ExtractionComponentFactory
from pathlib import Path

# Создание пайплайна extraction
pipeline = ExtractionComponentFactory.create_default_extraction_pipeline()

# Обработка изображения
result = pipeline.process_image(Path("data/input/receipt.jpg"))

# Результат - словарь с raw_ocr данными
raw_ocr_file = result['file_path']  # data/output/raw_ocr/receipt/raw_ocr.json
```

### Замена компонентов

```python
from src.extraction.application.factory import ExtractionComponentFactory

# Кастомный провайдер OCR (например, для GPT-4 Vision)
pipeline = ExtractionComponentFactory.create_extraction_pipeline(
    ocr_provider=CustomOCRProvider()
)

# Кастомный препроцессор
pipeline = ExtractionComponentFactory.create_extraction_pipeline(
    image_preprocessor=CustomImagePreprocessor()
)
```

## Домен Parsing

### Ответственность
- Обработка layout сырых данных OCR
- Определение локали чека
- Извлечение метаданных (магазин, дата, сумма, адрес, реквизиты)
- Семантическое извлечение товаров (название, количество, цена)
- Сохранение структурированных результатов

### Интерфейсы
- `IReceiptParser` - интерфейс для парсеров чеков
- `ILayoutProcessor` - интерфейс для обработки layout
- `ILocaleDetector` - интерфейс для детектора локали
- `IMetadataExtractor` - интерфейс для извлечения метаданных
- `ISemanticExtractor` - интерфейс для семантического извлечения
- `IParsingPipeline` - интерфейс для пайплайна parsing

### Использование

```python
from src.parsing.application.factory import ParsingComponentFactory
from pathlib import Path

# Создание пайплайна parsing
pipeline = ParsingComponentFactory.create_default_parsing_pipeline()

# Обработка raw_ocr файла
result = pipeline.process_ocr_file(Path("data/output/raw_ocr/receipt/raw_ocr.json"))

# Результат - структурированные данные чека
data = result['data']
print(f"Локаль: {data.get('locale')}")
print(f"Магазин: {data.get('metadata', {}).get('store_name')}")
print(f"Товаров: {len(data.get('items', []))}")
```

### Замена компонентов

```python
from src.parsing.application.factory import ParsingComponentFactory

# Кастомный семантический экстрактор (например, для AI-based parsing)
pipeline = ParsingComponentFactory.create_parsing_pipeline(
    semantic_extractor=CustomSemanticExtractor()
)

# Кастомный детектор локали
pipeline = ParsingComponentFactory.create_parsing_pipeline(
    receipt_parser=ParsingComponentFactory.create_receipt_parser(
        locale_detector=CustomLocaleDetector()
    )
)
```

## Точка входа (scripts/run_pipeline.py)

Точка входа для запуска полного пайплайна (Extraction + Parsing).

### Использование

```bash
# Обработать все изображения из data/input/
python scripts/run_pipeline.py

# Обработать конкретное изображение
python scripts/run_pipeline.py path/to/image.jpg

# Принудительный перезапуск (игнорировать кэш)
python scripts/run_pipeline.py --no-cache
```

### Поток выполнения

```
[data/input/IMG_XXXX.jpeg]
    ↓
[scripts/run_pipeline.py]
    ↓
┌─────────────────────────────────────┐
│  Extraction домен (независимый)   │
│  - Preprocessing                  │
│  - OCR (Google Vision)            │
│  - Сохранение raw_ocr.json        │
└─────────────────────────────────────┘
    ↓
[data/output/raw_ocr/IMG_XXXX/raw_ocr.json]
    ↓
┌─────────────────────────────────────┐
│   Parsing домен (независимый)     │
│   - Layout processing              │
│   - Locale detection              │
│   - Metadata extraction           │
│   - Semantic extraction            │
│   - Сохранение result.json        │
└─────────────────────────────────────┘
    ↓
[data/output/IMG_XXXX/result.json]
```

## Контракты между доменами

### Архитектура контрактов

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ЗОНА СВОБОДЫ (D1 → D2)                         │
│                                                                     │
│   D1 (Extraction)  ───────────→  D2 (Parsing)                       │
│                                                                     │
│   - Любая структура данных                                          │
│   - Оптимизируем для качества 100%                                  │
│   - МЫ АВТОРЫ                                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 ЖЕСТКИЕ КОНТРАКТЫ (1 в 1 с finpi_parser_photo)      │
│                                                                     │
│   D2 ──→ D3:           RawReceiptDTO                                │
│   D3 ──→ Orchestrator: ParseResultDTO                               │
│                                                                     │
│   НЕЛЬЗЯ МЕНЯТЬ - внешние сервисы зависят                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Верифицированные контракты (2025-12-29)

| Контракт | Наш файл | Источник истины | Статус |
|----------|----------|-----------------|--------|
| D1 → D2 | `contracts/d1_extraction_dto.py` | Наш дизайн | Гибкий |
| D2 → D3 | `contracts/d2_parsing_dto.py` | `finpi_parser_photo/domain/dto/raw_receipt_dto.py` | **1 в 1** |
| D3 → Orchestrator | `contracts/d3_categorization_dto.py` | `finpi_parser_photo/domain/dto/parse_receipt_dto.py` | **1 в 1** |

### D1 → D2: RawOCRResult (Гибкий)

Структура данных от Extraction к Parsing. Наша зона - определяем сами.

```python
@dataclass
class RawOCRResult:
    full_text: str
    blocks: List[TextBlock]       # Текстовые блоки с bounding boxes
    raw_annotations: List[Dict]   # Сырые аннотации от OCR
    metadata: Optional[OCRMetadata]
```

### D2 → D3: RawReceiptDTO (Жесткий, 1 в 1)

Структура данных от Parsing к Categorization. **Нельзя менять.**

```python
class RawReceiptItem(BaseModel):
    name: str                     # Название товара
    quantity: float | None
    price: float | None
    total: float | None
    date: datetime | None

class RawReceiptDTO(BaseModel):
    items: list[RawReceiptItem]
    total_amount: float | None
    merchant: str | None
    store_address: str | None
    date: datetime | None
    receipt_id: str | None
    ocr_text: str | None
    detected_locale: str | None
    metrics: dict[str, float]
```

### D3 → Orchestrator: ParseResultDTO (Жесткий, 1 в 1)

Финальный результат системы. **Нельзя менять.**

```python
class ReceiptItem(BaseModel):
    name: str
    quantity: float | None
    price: float | None
    total: float | None
    product_type: str           # L1
    product_category: str       # L2
    product_subcategory_l1: str # L3
    product_subcategory_l2: str | None  # L4
    product_subcategory_l3: list[str] | None  # L5
    needs_manual_review: bool | None
    merchant: str | None
    store_address: str | None
    date: datetime | None

class ParseResultDTO(BaseModel):
    success: bool
    items: list[ReceiptItem]
    sums: ReceiptSums | None
    error: str | None
    receipt_id: str | None
    data_validity: DataValidityInfo | None
    total_amount: float | None  # deprecated
```

**Почему это важно:**
- D2→D3 и D3→Orchestrator - публичные контракты
- Внешние сервисы (Telegram, Frontend) зависят от них
- D1→D2 - наша зона, оптимизируем для качества

## Система локалей

### Структура

```
src/parsing/locales/
├── de_DE/
│   └── config.yaml          # Конфигурация Германии
├── pl_PL/
│   └── config.yaml          # Конфигурация Польши
├── [98 других локалей]
├── locale_config.py         # DTO конфигурации локали
├── locale_config_loader.py   # Загрузчик YAML конфигураций
└── locale_detector.py        # Детектор локали
```

### Конфигурация локали (пример: de_DE/config.yaml)

```yaml
locale:
  code: de_DE
  name: Germany
  language: de
  region: DE
  rtl: false

currency:
  code: EUR
  symbol: "€"
  decimal_separator: ","
  thousands_separator: "."
  symbol_position: after
  format: "1.234,56"

date_formats:
  - "DD.MM.YYYY"
  - "DD.MM.YY"
  - "DD.MM."

patterns:
  total_keywords:
    - "gesamtbetrag"
    - "summe"
    - "zu zahlen"
  discount_keywords:
    - "preisvorteil"
    - "rabatt"
  noise_keywords:
    - "tel."
    - "fax."
    - "obj.-nr."

extractors:
  store_detection:
    known_brands:
      - "rewe"
      - "aldi"
      - "lidl"
  total_detection:
    bottom_n_lines: 10
    amount_range: [0.01, 100000.0]
```

## Масштабирование на 100+ локалей

### Текущее состояние
- ✅ Независимые домены (Extraction, Parsing)
- ✅ Контракт между доменами (RawOCRResult)
- ✅ Интерфейсы и адаптеры
- ✅ Система локалей через YAML
- ✅ Чистый код (без `sys.path` манипуляций в файлах внутри `src/`)

### Следующие шаги для масштабирования

1. **Валидация YAML конфигураций локалей**
   - Pydantic для валидации структуры
   - Проверка обязательных полей
   - Понятные ошибки при невалидной конфигурации

2. **Фолбэк-локаль**
   - Настроить дефолтную локаль (например, `en_US` или `de_DE`)
   - Логирование случаев использования фолбэка
   - Предупреждения о необходимости добавить конфигурацию

3. **Централизованный реестр локалей**
   - Автоматическое сканирование папки `locales/`
   - Регистрация всех локалей при старте
   - Метод `get_available_locales()`

4. **Кэширование конфигураций**
   - Не загружать YAML файл каждый раз
   - Кэшировать в памяти

5. **Мониторинг и логирование**
   - Логировать время выполнения по этапам
   - Логировать время для каждой локали
   - Метрики успеха/неудач

6. **Контракт для Parsing**
   - Определить структуру результатов Parsing
   - Стабильный контракт для клиентов (Telegram, Frontend, Google Sheets)

## Принципы разработки

1. **Systemic-First Principle**
   - Решать проблемы на архитектурном уровне
   - Использовать абстракции (`locales/`) вместо локальных фиксов
   - Решения должны масштабироваться на 100+ стран

2. **No Pivot Rule**
   - Google Vision OCR - основная технология
   - Оптимизация внутри текущего стека
   - Не менять технологию без крайней необходимости

3. **Immutable Boundaries**
   - Публичный контракт API сохраняется
   - Внутренняя реализация может меняться
   - При необходимости - адаптерный слой

## Заключение

Архитектура Finpi OCR спроектирована для масштабирования на 100+ локалей и 100000+ вариаций чеков.

**Ключевые преимущества:**
- Независимые домены → параллельная разработка
- Стабильный контракт → безопасная эволюция
- Интерфейсы и адаптеры → гибкость замены компонентов
- Система локалей → поддержка 100+ стран
- Чистый код → легкая поддержка и тестирование

