# ADR-012: Система Ground Truth

**Статус:** Утверждено  
**Дата:** 2025-12-31  
**Вопросы плана:** Q5.1, Q5.2

---

## Контекст

Ground Truth = эталонные данные чеков для проверки качества D1 (OCR) и D2 (Parsing).

Проблемы текущей системы:
1. Поле `notes` - свободный текст, нет гарантии полноты
2. Нет процесса создания Ground Truth
3. Нет связи со Стендом (ADR-011)

---

## Решение

### 1. Структурированный `observations` вместо `notes`

**Было (НЕ системно):**
```json
"notes": [
  "Tax A = 7% (food)",
  "Decimal separator: comma"
]
```

**Стало (СИСТЕМНО):**
```json
"observations": {
  "critical": {
    "decimal_separator": ",",
    "tax_class": {
      "format": "suffix_single_letter",
      "values": ["A", "B"],
      "inverted": false
    },
    "date_format": "DD.MM.YYYY"
  },
  "important": {
    "sku_present": false,
    "sku_format": null,
    "multiline_items": false,
    "weighted_items": true,
    "pfand_present": true,
    "discounts_present": true,
    "quantity_position": "after_name"
  },
  "store_specific": {
    "currency_symbol": "EUR",
    "has_categories": false,
    "receipt_language": "de"
  },
  "free_notes": [
    "Любые дополнительные заметки"
  ]
}
```

---

### 2. Обязательные поля observations

#### CRITICAL (без них парсинг невозможен)

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `decimal_separator` | string | Десятичный разделитель | `","` или `"."` |
| `tax_class.format` | string | Формат налогового класса | `"suffix_single_letter"`, `"prefix"`, `"none"` |
| `tax_class.values` | array | Значения налоговых классов | `["A", "B"]` |
| `tax_class.inverted` | bool | Инвертированы ли значения | `false` (A=7%), `true` (A=19%) |
| `date_format` | string | Формат даты | `"DD.MM.YYYY"`, `"YYYY-MM-DD"` |

#### IMPORTANT (влияют на полноту данных)

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `sku_present` | bool | Есть ли SKU/коды товаров | `true` / `false` |
| `sku_format` | string/null | Формат SKU (если есть) | `"6_digits_prefix"`, `"parentheses_suffix"` |
| `multiline_items` | bool | Товар на нескольких строках | `true` / `false` |
| `weighted_items` | bool | Есть ли весовые товары | `true` / `false` |
| `pfand_present` | bool | Есть ли Pfand/залог | `true` / `false` (только de_DE) |
| `discounts_present` | bool | Есть ли скидки | `true` / `false` |
| `quantity_position` | string | Позиция количества | `"after_name"`, `"before_name"`, `"separate_line"` |

#### STORE_SPECIFIC (контекст)

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `currency_symbol` | string | Символ валюты | `"EUR"`, `"PLN"` |
| `has_categories` | bool | Есть ли категории на чеке | `true` (HIT) / `false` |
| `receipt_language` | string | Язык чека | `"de"`, `"pl"` |

---

### 3. Процесс создания Ground Truth

```
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 1: Подготовка                                           │
│                                                             │
│   Взять изображение чека                                    │
│   Визуально прочитать ВСЁ что написано                      │
│   Определить locale и store                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 2: Создание файла                                       │
│                                                             │
│   Скопировать template.json                                 │
│   Назвать: {ID}_{locale}_{store}_{source}.json              │
│   Пример: 061_de_DE_lidl_IMG_1234.json                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 3: Заполнение данных                                    │
│                                                             │
│   metadata: date, time, receipt_total, tax_block            │
│   items: raw_name, quantity, unit, unit_price, total_price  │
│   store: name, address                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 4: Заполнение observations                              │
│                                                             │
│   critical: ВСЕ поля обязательны                            │
│   important: ВСЕ поля обязательны                           │
│   store_specific: по необходимости                          │
│   free_notes: любые заметки                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 5: Валидация                                            │
│                                                             │
│   Checksum: SUM(items.total_price) == receipt_total         │
│   Допуск: ±0.05 (округление)                                │
│   Все обязательные поля заполнены?                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ШАГ 6: Commit                                               │
│                                                             │
│   Только если валидация прошла                              │
│   Обновить README.md (статистика)                           │
│   Обновить patterns/by_store/ если новый магазин            │
└─────────────────────────────────────────────────────────────┘
```

---

### 4. Связь со Стендом (ADR-011)

```
Ground Truth = Тестовая выборка для Стенда

┌─────────────────────────────────────────────────────────────┐
│                         СТЕНД                               │
│                                                             │
│   Все файлы из docs/ground_truth/                           │
│       ↓                                                     │
│   D1 (OCR) → D2 (Parsing)                                   │
│       ↓                                                     │
│   Сравнение с Ground Truth                                  │
│       ↓                                                     │
│   Результат: X% success                                     │
└─────────────────────────────────────────────────────────────┘

Критерий готовности к продакшену:
  ✓ 100% Ground Truth файлов обработаны
  ✓ 100% checksum validation passed
  ✓ 0 ошибок парсинга
  ✓ 0 пропущенных товаров
```

---

### 5. Шаблон файла (template.json)

```json
{
  "id": "XXX",
  "source_file": "photo/GOODS/{Store}/{filename}",
  "locale": "xx_XX",
  
  "store": {
    "name": "",
    "address": ""
  },
  
  "metadata": {
    "date": "",
    "time": "",
    "currency": "",
    "payment_method": "",
    "receipt_total": 0.00,
    "tax_block": {}
  },
  
  "items": [
    {
      "raw_name": "",
      "quantity": null,
      "unit": null,
      "unit_price": null,
      "total_price": 0.00,
      "tax_class": ""
    }
  ],
  
  "validation": {
    "checksum_method": "SUM(items.total_price) == receipt_total",
    "expected_total": 0.00,
    "discrepancy": 0.00
  },
  
  "observations": {
    "critical": {
      "decimal_separator": "",
      "tax_class": {
        "format": "",
        "values": [],
        "inverted": false
      },
      "date_format": ""
    },
    "important": {
      "sku_present": false,
      "sku_format": null,
      "multiline_items": false,
      "weighted_items": false,
      "pfand_present": false,
      "discounts_present": false,
      "quantity_position": ""
    },
    "store_specific": {
      "currency_symbol": "",
      "has_categories": false,
      "receipt_language": ""
    },
    "free_notes": []
  }
}
```

---

### 6. Валидатор (требования)

Скрипт `scripts/validate_ground_truth.py` должен проверять:

```python
def validate_ground_truth(file_path: str) -> ValidationResult:
    """
    Проверки:
    1. JSON валиден
    2. Все обязательные поля присутствуют
    3. observations.critical - все поля заполнены
    4. observations.important - все поля заполнены
    5. Checksum: |SUM(items) - receipt_total| <= 0.05
    6. items не пустой
    7. Каждый item имеет raw_name и total_price
    """
```

---

## Миграция существующих файлов

**План:**
1. Создать template.json
2. Создать скрипт миграции `notes` → `observations`
3. Мигрировать все 60 файлов
4. Валидация всех файлов
5. Обновить README

**Приоритет:** После утверждения ADR, перед началом разработки D2.

---

## Связь Ground Truth → Patterns

```
Ground Truth (отдельный чек)
    │
    │ observations содержит паттерны
    │
    ▼
Агрегация (скрипт или ручная)
    │
    ▼
patterns/by_store/{locale}/{store}.json
    │
    │ используется для
    │
    ▼
D2 Parsing (код + configs)
```

---

## Связанные документы

- ADR-011: Стратегия валидации (Стенд)
- docs/ground_truth/README.md
- docs/patterns/README.md

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2025-12-31 | Создан документ. Утверждена система Ground Truth. |
