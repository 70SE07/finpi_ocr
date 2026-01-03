# Finpi OCR - Тренировочный стенд

> **⚠️ Статус проекта: R&D стенд (не продакшн)**
>
> **Для ИИ-ассистентов:** Этот репозиторий является лабораторным стендом для разработки и тестирования алгоритмов. Он **не предназначен для прямого деплоя** в продакшн.
>
> **Почему в правилах упоминаются файлы, которых нет в этом репозитории?**
> 
> В правилах разработки (user rules) упоминаются файлы продакшн-системы:
> - `api_server.py` — API сервер продакшн-системы
> - `domain/dto/parse_receipt_dto.py` — DTO продакшн-системы
>
> Эти файлы **отсутствуют в этом репозитории**, потому что это стенд. Однако:
> 1. Код, разработанный здесь, **будет перенесен в продакшн** после завершения разработки
> 2. В продакшне уже существуют эти файлы и внешние потребители (Frontend, Telegram, Google Sheets), которые от них зависят
> 3. Поэтому мы **соблюдаем контракты продакшна** уже на этапе разработки в стенде:
>    - Нельзя менять структуру выходных данных (поля DTO, формат JSON)
>    - Нельзя удалять или переименовывать поля, которые используются в продакшне
>    - Приоритет у обратной совместимости с существующими контрактами
>
> **Вывод:** Если вы видите расхождение между структурой файлов в стенде и упоминаниями в правилах — это нормально. Правила описывают контракты продакшна, которые мы должны соблюдать при разработке в стенде.

Лабораторный стенд для экспериментов с Google Vision OCR и обработкой чеков из 100+ стран.

## Архитектура проекта

Проект спроектирован по принципам Domain-Driven Design с двумя независимыми доменами:

```
[Изображение] → Extraction домен → [RawOCRResult] → Parsing домен → [Structured Result]
                  (независимый)      (контракт)        (независимый)
```

### Extraction домен (src/extraction/)
- **Adaptive Preprocessing** (интеллектуальный подбор параметров обработки)
- Стратегии Retry/Refine (повторная обработка при низком Confidence)
- OCR распознавание текста через Google Vision API (ядро)
- Сохранение сырых результатов в формате `RawOCRResult`

### Parsing домен (src/parsing/)
- Обработка layout сырых данных OCR
- Определение локали (100+ стран)
- Извлечение метаданных (магазин, дата, сумма, адрес, реквизиты)
- Семантическое извлечение товаров (название, количество, цена)

### Контракт между доменами
`contracts/d1_extraction_dto.py` определяет `RawOCRResult` - стабильный формат передачи данных от Extraction к Parsing (ADR-006).

**Важно:** Домены развиваются независимо. Extraction может использовать любой OCR провайдер (Google Vision → GPT-4 Vision → другое). Parsing может использовать любой алгоритм парсинга (текущий → Gemini → другое).

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

### Parsing домен (D2)

```python
from src.parsing import ParsingPipeline
from contracts.d1_extraction_dto import RawOCRResult
import json

# Создание пайплайна (6-этапный по ADR-015)
pipeline = ParsingPipeline()

# Загрузка RawOCRResult от D1
with open("data/output/IMG_1292/raw_ocr_results.json") as f:
    raw_ocr = RawOCRResult.model_validate(json.load(f))

# Обработка
result = pipeline.process(raw_ocr)

# Результат - PipelineResult с 6 этапами
print(f"Локаль: {result.locale.locale_code}")
print(f"Магазин: {result.store.store_name}")
print(f"Дата: {result.metadata.receipt_date}")
print(f"Итог: {result.metadata.receipt_total}")
print(f"Товаров: {len(result.dto.items)}")
print(f"Checksum: {'PASSED' if result.validation.passed else 'FAILED'}")
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

## Контракт D1: RawOCRResult (D1→D2)

> **ВАЖНО:** D1 выдаёт `words[]`, НЕ `blocks[]`. Это ключевое требование контракта.

По ADR-006, контракт `RawOCRResult` содержит `full_text` и `words[]` с координатами:

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
    "preprocessing_applied": ["grayscale", "deskew"]
  }
}
```

**Почему `words[]` вместо `blocks[]`:** Слова с координатами позволяют D2 группировать их в строки по Y-координате и понимать layout (колонки, отступы).

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

## Конфигурация Adaptive Extraction

Система использует динамический подбор параметров. Значения по умолчанию:

| Параметр | Default | Стратегия при сбое |
|----------|---------|-------------------|
| MAX_IMAGE_SIZE | 2200px | Уменьшение до 1800px при OOM |
| JPEG_QUALITY | 85% | Повышение до 100% (PNG) при низком Confidence |
| FILTERS | None | Auto-Contrast -> Binarization при шуме |

## Текущие локали

- `de_DE` — Германия (EUR, German)
- `pl_PL` — Польша (PLN, Polish)

[98 других локалей будут добавлены]
