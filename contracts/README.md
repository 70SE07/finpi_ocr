# Contracts - DTO контракты между доменами

Этот модуль содержит официальные контракты (DTO) для передачи данных между доменами системы.

---

## Статус контрактов

**Дата:** 2025-12-29

| Контракт | Файл | Источник истины | Статус |
|----------|------|-----------------|--------|
| D1 к D2 | d1_extraction_dto.py | Наш дизайн (ADR-006) | Принято |
| D2 к D3 | d2_parsing_dto.py | finpi_parser_photo | 1 в 1 |
| D3 к Orchestrator | d3_categorization_dto.py | finpi_parser_photo | 1 в 1 |

---

## Архитектура контрактов

ЗОНА СВОБОДЫ (D1 к D2):
- Решение (ADR-006): full_text + words[] с координатами
- Цель: 99.9% качества парсинга
- МЫ АВТОРЫ

ЖЕСТКИЕ КОНТРАКТЫ (] с координатами.

RawOCRResult:
- full_text: str - Длнов, определения локали
- words: List[Word] - Для layout, структуры, точного извлечения
- metadata: OCRMetadata - Метаданные обработки

Word:
- text: str - Текст слова
- bounding_box: BoundingBox - Координаты (x, y, width, height)
- confidence: float - Уверенность OCR (0.0 - 1.0)

### d2_parsing_dto.py - D2 к D3 (Жесткий, 1 в 1)

Источник: finpi_parser_photo/domain/dto/raw_receipt_dto.py

RawReceiptItem: name, quantity, price, total, date
RawReceiptDTO: items, total_amount, merchant, store_address, date, receipt_id, ocr_text, detected_locale, metrics

### d3_categorization_dto.py - D3 к Orchestrator (Жесткий, 1 в 1)

Источник: finpi_parser_photo/domain/dto/parse_receipt_dto.py

ReceiptItem: name, quantity, price, total, product_type, product_category, product_subcategory_l1/l2/l3, needs_manual_review, merchant, store_address, date
ParseResultDTO: success, items, sums, error, rным API.

ЗАПРЕЩЕНО: изменять названия полей, удалять поля, менять типы данных
РАЗРЕШЕНО: добавлять новые опциональные поля в конец

---

## Связанная документация

- docs/architecture/decisions/004_dto_contracts.md
- docs/architecture/decisions/005_contract_boundaries.md
- docs/architecture/decisions/006_d1_d2_contract_design.md
