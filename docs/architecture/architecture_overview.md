# Архитектура проекта Finpi OCR

## Обзор

Finpi OCR - тренировочный стенд для экспериментов с Google Vision OCR и обработкой чеков из 100+ стран.

## Три домена системы

Система разделена на три независимых домена согласно принципу SRP (Single Responsibility Principle).

| Домен | Название | ЦКП (Ценный Конечный Продукт) | Вход | Выход |
|-------|----------|-------------------------------|------|-------|
| **D1** | Extraction | Оцифрованный текст без потерь | Изображение чека | `RawOCRResult` |
| **D2** | Parsing | Структурированные данные чека | `RawOCRResult` | `RawReceiptDTO` |
| **D3** | Categorization | Категоризированные товары (L1-L5) | `RawReceiptDTO` | `ParseResultDTO` |

### Принципы разделения

1. **D1 (Extraction)** - language-agnostic
   - Не знает о языках и локалях
   - Google Vision сам определяет язык
   - Задача: оцифровать текст с изображения

2. **D2 (Parsing)** - locale-aware
   - Определяет локаль чека
   - Извлекает структуру (товары, цены, метаданные)
   - Работает с YAML-конфигурациями локалей

3. **D3 (Categorization)** - внешний домен
   - Реализован в `finpi_parser_photo/`
   - Использует LLM + Constitution + Directories
   - Не наша зона ответственности

### Подробная документация

| Тема | Документ |
|------|----------|
| Почему 3 домена | [ADR-001: Разделение на домены](decisions/001_domain_separation.md) |
| ЦКП каждого домена | [ADR-002: Ответственности доменов](decisions/002_domain_responsibilities.md) |
| Архитектура D3 | [ADR-007: D3 Categorization](decisions/007_d3_categorization_overview.md) |

## Принципы проектирования

1. **Независимые домены (Domain-Driven Design)**
   - Extraction домен: preprocessing + OCR
   - Parsing домен: layout, locale, metadata, semantic extraction
   - Домены изолированы и могут развиваться независимо

2. **Контракт между доменами (Pydantic)**
   - D1→D2: `contracts/d1_extraction_dto.py` — `RawOCRResult` (words + full_text)
   - D2→D3: `contracts/d2_parsing_dto.py` — `RawReceiptDTO`
   - D3→Orchestrator: `contracts/d3_categorization_dto.py` — `ParseResultDTO`

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
├── contracts/                 # Контракты между доменами (Pydantic)
│   ├── d1_extraction_dto.py  # D1→D2: RawOCRResult
│   ├── d2_parsing_dto.py     # D2→D3: RawReceiptDTO
│   └── d3_categorization_dto.py # D3→Orchestrator
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
│   │   ├── infrastructure/    # Реализации
│   │   │   ├── ocr/
│   │   │   │   └── google_vision_ocr.py  # GoogleVisionOCR (Google Vision API)
│   │   │   └── file_manager.py       # ExtractionFileManager
│   │   │
│   │   └── pre_ocr/         # Preprocessing
│   │       ├── pipeline.py         # PreOCRPipeline (оркестратор)
│   │       ├── image_file_reader.py # ImageFileReader
│   │       ├── image_encoder.py     # ImageEncoder
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
    image_preprocessor=CustomPreOCRPipeline()
)
```

## Домен Parsing

### Ответственность
- Обработка layout сырых данных OCR
- Определение локали чека
- Извлечение метаданных (магазин, дата, сумма, адрес, реквизиты)
- Семантическое извлечение товаров (название, количество, цена)
- Сохранение структурированных результатов

### Архитектура (6-этапный пайплайн по ADR-015)

```
src/parsing/stages/
├── stage_1_layout.py      # Layout: группировка слов в строки
├── stage_2_locale.py      # Locale: определение языка/локали
├── stage_3_store.py       # Store: определение магазина
├── stage_4_metadata.py    # Metadata: дата, сумма, валюта
├── stage_5_semantic.py    # Semantic: извлечение товаров
├── stage_6_validation.py  # Validation: checksum
└── pipeline.py            # ParsingPipeline (оркестратор)
```

### Использование

```python
from src.parsing import ParsingPipeline
from contracts.d1_extraction_dto import RawOCRResult
import json

# Создание пайплайна
pipeline = ParsingPipeline()

# Загрузка RawOCRResult от D1
with open("data/output/IMG_1292/raw_ocr_results.json") as f:
    raw_ocr = RawOCRResult.model_validate(json.load(f))

# Обработка (6 этапов)
result = pipeline.process(raw_ocr)

# Результат
print(f"Локаль: {result.locale.locale_code}")
print(f"Магазин: {result.store.store_name}")
print(f"Дата: {result.metadata.receipt_date}")
print(f"Итог: {result.metadata.receipt_total}")
print(f"Товаров: {len(result.dto.items)}")
print(f"Checksum: {'PASSED' if result.validation.passed else 'FAILED'}")
```

### Локализация

```
src/parsing/locales/
├── config_loader.py       # ConfigLoader - загрузка конфигов
├── de_DE/
│   ├── parsing.yaml       # Паттерны для немецкого
│   └── stores.yaml        # Магазины
├── pl_PL/
├── pt_PT/
└── ...
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

### Верифицированные контракты

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

