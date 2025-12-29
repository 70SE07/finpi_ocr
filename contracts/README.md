# Contracts - DTO контракты между доменами

Этот модуль содержит официальные контракты (DTO) для передачи данных между доменами системы.

---

## Статус верификации

**Дата:** 2025-12-29  
**Верификация:** Поле-за-полем сверка с `finpi_parser_photo`

| Контракт | Файл | Источник истины | Статус |
|----------|------|-----------------|--------|
| D2 → D3 | `d2_parsing_dto.py` | `finpi_parser_photo/domain/dto/raw_receipt_dto.py` | **1 в 1** |
| D3 → Orchestrator | `d3_categorization_dto.py` | `finpi_parser_photo/domain/dto/parse_receipt_dto.py` | **1 в 1** |
| D1 → D2 | `d1_extraction_dto.py` | Наш дизайн | Гибкий |

---

## Архитектура контрактов

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ЗОНА СВОБОДЫ (D1 → D2)                         │
│                                                                     │
│   - Любая структура данных                                          │
│   - Оптимизируем для качества 99.9%                                 │
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

---

## Файлы контрактов

### `d1_extraction_dto.py` - D1 → D2 (Гибкий)

Результат OCR. Наша зона - структура определяется нами.

### `d2_parsing_dto.py` - D2 → D3 (Жесткий, 1 в 1)

**Источник:** `finpi_parser_photo/domain/dto/raw_receipt_dto.py`

| Класс | Описание |
|-------|----------|
| `RawReceiptItem` | Товар без категоризации |
| `RawReceiptDTO` | Чек с raw данными |

**RawReceiptItem:**
| Поле | Тип | Required |
|------|-----|----------|
| `name` | `str` | да |
| `quantity` | `float \| None` | нет |
| `price` | `float \| None` | нет |
| `total` | `float \| None` | нет |
| `date` | `datetime \| None` | нет |

**RawReceiptDTO:**
| Поле | Тип | Required |
|------|-----|----------|
| `items` | `list[RawReceiptItem]` | да |
| `total_amount` | `float \| None` | нет |
| `merchant` | `str \| None` | нет |
| `store_address` | `str \| None` | нет |
| `date` | `datetime \| None` | нет |
| `receipt_id` | `str \| None` | нет |
| `ocr_text` | `str \| None` | нет |
| `detected_locale` | `str \| None` | нет |
| `metrics` | `dict[str, float]` | да |

### `d3_categorization_dto.py` - D3 → Orchestrator (Жесткий, 1 в 1)

**Источник:** `finpi_parser_photo/domain/dto/parse_receipt_dto.py`

| Класс | Описание |
|-------|----------|
| `ReceiptItem` | Товар с категоризацией L1-L5 |
| `ReceiptSums` | Сводные суммы |
| `DataValidityInfo` | Информация о валидации |
| `ParseResultDTO` | Финальный результат |

**ReceiptItem:**
| Поле | Тип | Required |
|------|-----|----------|
| `name` | `str` | да |
| `quantity` | `float \| None` | нет |
| `price` | `float \| None` | нет |
| `total` | `float \| None` | нет |
| `product_type` | `str` | да |
| `product_category` | `str` | да |
| `product_subcategory_l1` | `str` | да |
| `product_subcategory_l2` | `str \| None` | нет |
| `product_subcategory_l3` | `list[str] \| None` | нет |
| `needs_manual_review` | `bool \| None` | нет |
| `merchant` | `str \| None` | нет |
| `store_address` | `str \| None` | нет |
| `date` | `datetime \| None` | нет |

**ParseResultDTO:**
| Поле | Тип | Required |
|------|-----|----------|
| `success` | `bool` | да |
| `items` | `list[ReceiptItem]` | да |
| `sums` | `ReceiptSums \| None` | нет |
| `error` | `str \| None` | нет |
| `receipt_id` | `str \| None` | нет |
| `data_validity` | `DataValidityInfo \| None` | нет |
| `total_amount` | `float \| None` | нет (deprecated) |

---

## Immutable Contract Rules

> **ВНИМАНИЕ**: Контракты D2→D3 и D3→Orchestrator являются публичным API.
> Внешние сервисы (Telegram, Frontend) зависят от этой структуры.

**ЗАПРЕЩЕНО:**
- Изменять названия полей
- Удалять существующие поля
- Менять типы данных
- Менять порядок полей

**РАЗРЕШЕНО:**
- Добавлять новые опциональные поля (в конец)
- Менять внутреннюю реализацию без изменения структуры

---

## Связанная документация

- [ADR-004: Контракты DTO](../docs/architecture/decisions/004_dto_contracts.md)
- [ADR-005: Границы контрактов](../docs/architecture/decisions/005_contract_boundaries.md)
