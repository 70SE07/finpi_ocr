# Finpi OCR - Тренировочный стенд

Лабораторный стенд для экспериментов с Google Vision OCR и обработкой чеков из 100+ стран.

## Архитектура проекта

Проект спроектирован по принципам Domain-Driven Design с двумя независимыми доменами:

```
[Изображение] → Extraction домен → [RawOCRResult] → Parsing домен → [Structured Result]
                  (независимый)      (контракт)        (независимый)
```

### Extraction домен (src/extraction/)
- Preprocessing изображений (deskew, rotation, grayscale, compression)
- OCR распознавание текста через Google Vision API
- Сохранение сырых результатов в формате `RawOCRResult`

### Parsing домен (src/parsing/)
- Обработка layout сырых данных OCR
- Определение локали (100+ стран)
- Извлечение метаданных (магазин, дата, сумма, адрес, реквизиты)
- Семантическое извлечение товаров (название, количество, цена)

### Контракт между доменами
`contracts/raw_ocr_schema.py` определяет `RawOCRResult` - стабильный формат передачи данных от Extraction к Parsing.

**Важно:** Домены развиваются независимо. Extraction может использовать любой OCR провайдер (Google Vision → GPT-4 Vision → другое). Parsing может использовать любой алгоритм парсинга (текущий → Gemini → другое).

## Структура проекта

```
Finpi_OCR/
├── config/                       # Настройки
│   ├── settings.py              # Параметры системы
│   └── google_credentials.json   # Google Cloud credentials (НЕ в git!)
│
├── contracts/                    # Контракты между доменами
│   └── raw_ocr_schema.py       # RawOCRResult (Extraction → Parsing)
│
├── data/                         # Данные
│   ├── input/                   # Входные изображения чеков
│   └── output/                  # Результаты обработки
│       └── raw_ocr/            # Сырые результаты OCR
│
├── docs/                         # Документация
│   ├── architecture/             # Архитектурные решения
│   │   ├── architecture_overview.md  # Обзор архитектуры
│   │   └── contract_registry.md      # Реестр контрактов модулей
│   └── hypotheses/              # Гипотезы и эксперименты
│
├── src/                          # Исходный код
│   ├── extraction/               # Домен Extraction (независимый)
│   │   ├── domain/              # Интерфейсы и исключения
│   │   ├── application/          # Factory + Pipeline
│   │   ├── infrastructure/       # Адаптеры и реализации
│   │   ├── ocr/                # Google Vision OCR
│   │   └── pre_ocr/            # Preprocessing
│   │
│   ├── parsing/                  # Домен Parsing (независимый)
│   │   ├── domain/              # Интерфейсы и исключения
│   │   ├── application/          # Factory + Pipeline
│   │   ├── infrastructure/       # Адаптеры и реализации
│   │   ├── locales/             # Конфигурации 100+ стран
│   │   ├── metadata/            # Экстракторы метаданных
│   │   ├── layout/              # Обработка layout
│   │   ├── extraction/           # Семантическое извлечение
│   │   └── old_project/         # Устаревший код (не используется)
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

## Быстрый старт

### 1. Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка Google Cloud credentials

1. Положите `google_credentials.json` в `config/`
2. Проверьте настройки в `config/settings.py`

### 3. Запуск полного пайплайна

```bash
# Обработать все изображения из data/input/
python scripts/run_pipeline.py

# Обработать конкретное изображение
python scripts/run_pipeline.py path/to/image.jpg

# Принудительный перезапуск (игнорировать кэш)
python scripts/run_pipeline.py --no-cache
```

## Использование через Python API

### Extraction домен

```python
from src.extraction.application.factory import ExtractionComponentFactory
from pathlib import Path

# Создание пайплайна extraction
pipeline = ExtractionComponentFactory.create_default_extraction_pipeline()

# Обработка изображения
result = pipeline.process_image(Path("data/input/receipt.jpg"))

# Результат - словарь с raw_ocr данными
raw_ocr_file = result['file_path']  # data/output/raw_ocr/receipt/raw_ocr.json
print(f"Сохранено: {raw_ocr_file}")
```

### Parsing домен

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

## Конфигурация локалей

Конфигурации локалей хранятся в `src/parsing/locales/` в формате YAML:

```
src/parsing/locales/
├── de_DE/
│   └── config.yaml          # Германия (EUR, German keywords, brands)
├── pl_PL/
│   └── config.yaml          # Польша (PLN, Polish keywords, brands)
├── [98 других локалей]
├── locale_config.py         # DTO конфигурации локали
├── locale_config_loader.py   # Загрузчик YAML конфигураций
└── locale_detector.py        # Детектор локали
```

Пример конфигурации (`de_DE/config.yaml`):

```yaml
locale:
  code: de_DE
  name: Germany
  language: de
  region: DE

currency:
  code: EUR
  symbol: "€"
  decimal_separator: ","
  thousands_separator: "."
  format: "1.234,56"

date_formats:
  - "DD.MM.YYYY"
  - "DD.MM.YY"

patterns:
  total_keywords:
    - "gesamtbetrag"
    - "summe"
    - "zu zahlen"
  known_brands:
    - "rewe"
    - "aldi"
    - "lidl"
```

## Масштабирование на 100+ локалей

### Текущее состояние
- ✅ Независимые домены (Extraction, Parsing)
- ✅ Контракт между доменами (RawOCRResult)
- ✅ Интерфейсы и адаптеры
- ✅ Система локалей через YAML
- ✅ Чистый код (без `sys.path` манипуляций в файлах внутри `src/`)

### Следующие шаги
1. Валидация YAML конфигураций локалей через Pydantic
2. Фолбэк-локаль для неопределенных случаев
3. Централизованный реестр локалей
4. Кэширование конфигураций
5. Мониторинг и логирование
6. Контракт для Parsing (Structured Result)

## Документация

Подробная архитектура и контракты:
- [Обзор архитектуры](docs/architecture/architecture_overview.md) — независимые домены, контракты, использование
- [Реестр контрактов](docs/architecture/contract_registry.md) — обязательства модулей

## Формат RawOCRResult

```json
{
  "metadata": {
    "timestamp": "2025-12-26T14:54:27",
    "source_file": "IMG_1292"
  },
  "full_text": "Полный текст чека...",
  "blocks": [
    {
      "text": "Строка текста",
      "confidence": 0.98,
      "bounding_box": {"x": 10, "y": 20, "width": 200, "height": 40},
      "block_type": "PARAGRAPH"
    }
  ],
  "raw_annotations": [...]
}
```

## Принципы разработки

1. **Systemic-First Principle**
   - Решать проблемы на архитектурном уровне
   - Использовать абстракции (`locales/`) вместо локальных фиксов
   - Решения масштабируются на 100+ стран

2. **No Pivot Rule**
   - Google Vision OCR - основная технология
   - Оптимизация внутри текущего стека
   - Не менять технологию без крайней необходимости

3. **Independent Domains**
   - Extraction и Parsing развиваются независимо
   - Контракт между доменами стабилен
   - Легкая замена реализаций через адаптеры

## Настройки Pre-OCR

| Параметр | Значение | Описание |
|----------|----------|----------|
| MAX_IMAGE_SIZE | 2200px | Максимальный размер стороны |
| JPEG_QUALITY | 85% | Качество сжатия |

## Текущие локали

- `de_DE` — Германия (EUR, German)
- `pl_PL` — Польша (PLN, Polish)

[98 других локалей будут добавлены]
