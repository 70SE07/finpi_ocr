# Контракты DTO между доменами

## Статус валидации

Все контракты используют **Pydantic v2** с валидацией:

| Контракт | Файл | Валидация | Статус |
|----------|------|-----------|--------|
| D1 -> D2 | `d1_extraction_dto.py` | ✅ Pydantic | **Готов** |
| D2 -> D3 | `d2_parsing_dto.py` | ✅ Pydantic | **1 в 1 с finpi_parser_photo** |
| D3 -> Orchestrator | `d3_categorization_dto.py` | ✅ Pydantic | **1 в 1 с finpi_parser_photo** |

---

## D1 -> D2: RawOCRResult

**Файл:** `d1_extraction_dto.py`

**Наш дизайн** (ADR-006). Передаёт:
- `full_text` — для regex, паттернов, определения локали
- `words[]` — для layout, структуры (X/Y координаты)
- `metadata` — информация об обработке

**Валидация:**
- `BoundingBox`: x, y >= 0; width, height > 0
- `Word`: text не пустой; confidence в [0.0, 1.0]
- `OCRMetadata`: source_file не пустой; размеры > 0

**Утилиты:**
- `get_words_in_region()` — слова в области
- `get_lines_by_y()` — группировка слов в строки

---

## D2 -> D3: RawReceiptDTO

**Файл:** `d2_parsing_dto.py`

**1 в 1 с `finpi_parser_photo/domain/dto/raw_receipt_dto.py`**

**Структура:**
```python
RawReceiptDTO:
    items: list[RawReceiptItem]  # name, quantity, price, total
    total_amount: float | None
    merchant: str | None
    store_address: str | None
    date: datetime | None
    receipt_id: str | None
    ocr_text: str | None
    detected_locale: str | None
    metrics: dict[str, float]
```

**Валидация:**
- `quantity` > 0
- `price`, `total` >= 0 (отрицательные НЕ допускаются — см. ADR-014)

---

## D3 -> Orchestrator: ParseResultDTO

**Файл:** `d3_categorization_dto.py`

**1 в 1 с `finpi_parser_photo/domain/dto/parse_receipt_dto.py`**

**Структура:**
```python
ParseResultDTO:
    success: bool
    items: list[ReceiptItem]  # + категоризация L1-L5
    sums: ReceiptSums | None
    error: str | None
    receipt_id: str | None
    data_validity: DataValidityInfo | None
```

**Валидация:**
- `product_type` in ["GOODS", "SERVICE"]
- `quantity` > 0

---

## Правила изменения контрактов

### D1 -> D2 (Наш дизайн)
- ✅ Можно добавлять новые поля
- ✅ Можно добавлять утилиты
- ❌ Нельзя удалять существующие поля

### D2 -> D3 и D3 -> Orchestrator (1 в 1)
- ❌ Нельзя изменять структуру
- ❌ Нельзя добавлять/удалять поля
- ❌ Нельзя менять типы данных

При изменениях в `finpi_parser_photo` — синхронизировать контракты.

---

## Связанные ADR

- [ADR-005: Contract Boundaries](../docs/architecture/decisions/005_contract_boundaries.md)
- [ADR-006: D1->D2 Contract Design](../docs/architecture/decisions/006_d1_d2_contract_design.md)
- [ADR-014: Edge Cases](../docs/architecture/decisions/014_edge_cases_handling.md) — ограничения отрицательных значений
