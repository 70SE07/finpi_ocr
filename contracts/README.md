# Contracts - DTO контракты между доменами

Этот модуль содержит официальные контракты (DTO) для передачи данных между доменами системы.

---

## Статус контрактов

**Дата верификации:** 2025-12-29

| Контракт | Файл | Источник истины | Статус |
|----------|------|-----------------|--------|
| D1 → D2 | `d1_extraction_dto.py` | Наш дизайн (ADR-006) | **Принято** |
| D2 → D3 | `d2_parsing_dto.py` | finpi_parser_photo | **1 в 1** |
| D3 → Orchestrator | `d3_categorization_dto.py` | finpi_parser_photo | **1 в 1** |

---

## Архитектура контрактов

### ЗОНА СВОБОДЫ (D1 → D2)

- **Решение (ADR-006):** full_text + words[] с координатами
- **Цель:** 100% качества парсинга
- **МЫ АВТОРЫ** - можем менять структуру

### ЖЕСТКИЕ КОНТРАКТЫ (D2 → D3, D3 → Orchestrator)

- **Источник истины:** finpi_parser_photo
- **Статус:** 1 в 1 верифицировано
- **НЕЛЬЗЯ менять** - внешние системы зависят

---

## Структура контрактов

### d1_extraction_dto.py - D1 → D2 (Гибкий, наш дизайн)

```python
@dataclass
class RawOCRResult:
    full_text: str           # Для regex, паттернов, локали
    words: List[Word]        # Для layout, структуры, точности
    metadata: OCRMetadata    # Метаданные обработки

@dataclass
class Word:
    text: str
    bounding_box: BoundingBox
    confidence: float
```

### d2_parsing_dto.py - D2 → D3 (Жесткий, 1 в 1)

**Источник:** `finpi_parser_photo/domain/dto/raw_receipt_dto.py`

```python
class RawReceiptItem(BaseModel):
    name: str
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

### d3_categorization_dto.py - D3 → Orchestrator (Жесткий, 1 в 1)

**Источник:** `finpi_parser_photo/domain/dto/parse_receipt_dto.py`

```python
class ReceiptItem(BaseModel):
    name: str
    quantity: float | None
    price: float | None
    total: float | None
    product_type: str           # L1: GOODS/SERVICE
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

---

## Правила изменения

### Жесткие контракты (D2→D3, D3→Orchestrator)

| Действие | Разрешено? |
|----------|------------|
| Изменять названия полей | ❌ НЕТ |
| Удалять поля | ❌ НЕТ |
| Менять типы данных | ❌ НЕТ |
| Добавлять опциональные поля | ✓ ДА (в конец) |

### Гибкий контракт (D1→D2)

| Действие | Разрешено? |
|----------|------------|
| Любые изменения | ✓ ДА (мы авторы) |
| Оптимизация структуры | ✓ ДА |
| Добавление полей | ✓ ДА |

---

## Связанная документация

- `docs/architecture/decisions/004_dto_contracts.md` - Контракты DTO
- `docs/architecture/decisions/005_contract_boundaries.md` - Границы контрактов
- `docs/architecture/decisions/006_d1_d2_contract_design.md` - Дизайн D1→D2
