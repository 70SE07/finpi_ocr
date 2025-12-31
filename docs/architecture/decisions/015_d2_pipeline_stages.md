# ADR-015: Этапы пайплайна D2 (Parsing)

## Статус
**Утверждено** (31.12.2024)

## Контекст

D2 (Parsing) получает сырые данные OCR от D1 и должен выдать структурированные данные чека для D3.

Нужно определить:
1. Какие этапы обработки (Q8.1)
2. В каком порядке (Q8.2)

## Решение

### Этапы пайплайна D2

| # | Этап | ЦКП этапа | Входные данные |
|---|------|-----------|----------------|
| 1 | **Layout Processing** | Структура чека (строки, колонки) | D1: words + coordinates |
| 2 | **Locale Detection** | Код локали (de_DE, pl_PL, ...) | Layout: full_text |
| 3 | **Store Detection** | Магазин + store config (опционально) | Locale config |
| 4 | **Metadata Extraction** | date, merchant, address, receipt_total | Locale/Store config |
| 5 | **Semantic Extraction** | Items (name, price, qty, tax, is_discount, is_pfand) | Locale config, Layout |
| 6 | **Validation** | Checksum passed ✓ | Items + receipt_total |

### Порядок выполнения

```
D1 Output (RawOCRResult)
         │
         ▼
    ┌─────────────────┐
    │ 1. Layout       │  ← Группировка слов в строки (Y), колонки (X)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 2. Locale       │  ← Определение локали по keywords, currency
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 3. Store        │  ← Определение магазина, загрузка store config
    └────────┬────────┘    (опционально, fallback на locale config)
             │
             ▼
    ┌─────────────────┐
    │ 4. Metadata     │  ← date, merchant, address, receipt_total
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 5. Items        │  ← name, price, qty, tax, discounts, pfand
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ 6. Validation   │  ← SUM(items.total) ≈ receipt_total
    └────────┬────────┘
             │
             ▼
    D2 Output (RawReceiptDTO)
```

## Обоснование порядка

### 1. Layout первый
- Без понимания структуры (строки, колонки) невозможно корректно парсить
- Использует координаты из D1 (words с bounding_box)
- Универсален для всех локалей

### 2. Locale перед Store
- Store config находится внутри locale: `locales/de_DE/stores/lidl.yaml`
- Без locale нельзя найти store config

### 3. Store после Locale
- Store переопределяет locale config только для исключений
- Опционален — система работает без store detection (fallback на locale)

### 4. Metadata перед Items
- Нужен `receipt_total` для валидации checksum
- date_formats, total_keywords берутся из locale config

### 5. Items — основной этап
- Главный ЦКП D2
- Использует decimal_separator, discount_patterns из locale config
- Использует layout для понимания структуры строк

### 6. Validation последний
- Проверка: `SUM(items.total) ≈ receipt_total`
- Tolerance: ±0.05 (округление)
- Если не сошлось → баг системы, нужно чинить D2

## Системность решения

> **Добавление 101-й локали = создание config файла, НЕ изменение кода.**

| Критерий | Выполнен |
|----------|----------|
| Конфигурация над кодом | ✅ Различия в YAML, не в Python |
| Иерархия locale → store | ✅ Исключения переопределяют базу |
| Универсальные алгоритмы | ✅ Layout по координатам, checksum по математике |
| Нет хардкода локалей | ✅ Паттерны в config, не в коде |

---

## Известные ограничения и планы улучшения

### Stage 1 (Layout): Фиксированный threshold

**Текущее решение:** `y_threshold=15` (пиксели) для группировки слов в строки.

**Ограничение:** Может не работать оптимально для:
- Чеков с разным размером шрифта
- Низкокачественных изображений
- Сильно наклонённых чеков

**План улучшения:** Сделать threshold адаптивным:
```python
# Вариант 1: Процент от высоты символа
threshold = avg_word_height * 0.5

# Вариант 2: Медиана расстояний между строками
threshold = median(line_gaps) * 0.8
```

**Когда реализовать:** После сбора статистики на 100+ реальных чеках.

### Stage 2 (Locale): Ложные срабатывания

**Текущее решение:** Определение локали по ключевым словам.

**Ограничение:** Одинаковые слова могут встречаться в разных языках.

**План улучшения:** Комбинация признаков:
1. Ключевые слова (текущее)
2. Формат даты (DD.MM.YYYY vs MM/DD/YYYY)
3. Символ валюты (€, zł, Kč)
4. Название известного магазина

**Когда реализовать:** При появлении первых ошибок определения локали.

---

## Связанные решения

- [ADR-002: ЦКП доменов](002_domain_responsibilities.md) — D2 гарантирует 100% качество
- [ADR-006: D1→D2 Contract](006_d1_d2_contract_design.md) — full_text + words с координатами
- [ADR-010: Locale/Store Hierarchy](010_locale_store_hierarchy.md) — иерархия конфигов
- [ADR-011: Validation Strategy](011_validation_strategy.md) — checksum, tolerance
- [ADR-014: Edge Cases](014_edge_cases_handling.md) — скидки, Pfand, 2-колоночные
