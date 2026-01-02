# ADR-004: Контракты DTO между доменами

**Статус:** Принято  
**Обновлено:** 2025-12-29  
**Вопрос плана:** Q2.0

---

## Контекст

Система состоит из 3 доменов:
- D1 (Extraction) - оцифровка чека
- D2 (Parsing) - структурирование данных
- D3 (Categorization) - категоризация товаров

Нужно определить контракты (DTO) между доменами.

**Ключевое требование:** Контракты должны быть 1 в 1 совместимы с существующими DTO в `finpi_parser_photo`.

---

## Вопрос

Какие данные передаются между доменами?

---

## Решение

### Контракты (1 в 1 с finpi_parser_photo)

| Контракт | Файл | Направление | Источник в finpi_parser_photo |
|----------|------|-------------|-------------------------------|
| RawOCRResult | `contracts/d1_extraction_dto.py` | D1 → D2 | - |
| RawReceiptDTO | `contracts/d2_parsing_dto.py` | D2 → D3 | `domain/dto/raw_receipt_dto.py` |
| ParseResultDTO | `contracts/d3_categorization_dto.py` | D3 → Оркестратор | `domain/dto/parse_receipt_dto.py` |

### D1 → D2: RawOCRResult

```python
@dataclass
class RawOCRResult:
    full_text: str                    # Полный текст
    blocks: List[TextBlock]           # Блоки с координатами
    raw_annotations: List[Dict]       # Raw аннотации
    metadata: Optional[OCRMetadata]
```

### D2 → D3: RawReceiptDTO (1 в 1 с finpi_parser_photo)

```python
class RawReceiptItem(BaseModel):
    name: str                         # Название как на чеке
    quantity: float | None            # Количество
    price: float | None               # Цена за единицу
    total: float | None               # Итоговая цена позиции
    date: datetime | None             # Дата (если есть)

class RawReceiptDTO(BaseModel):
    items: list[RawReceiptItem]       # Товары без категорий
    total_amount: float | None        # Итого по чеку
    merchant: str | None              # Название магазина
    store_address: str | None         # Адрес
    date: datetime | None             # Дата чека
    receipt_id: str | None            # ID чека
    ocr_text: str | None              # Raw OCR текст
    detected_locale: str | None       # Локаль
    metrics: dict[str, float]         # Метрики парсинга
```

**Важно:** RawReceiptItem НЕ содержит полей категоризации!

### D3 → Оркестратор: ParseResultDTO (1 в 1 с finpi_parser_photo)

```python
class ReceiptItem(BaseModel):
    # Данные товара
    name: str                         # Название
    quantity: float | None            # Количество
    price: float | None               # Цена за единицу
    total: float | None               # Итоговая цена
    
    # 5-уровневая категоризация
    product_type: str                 # L1: GOODS или SERVICE
    product_category: str             # L2: GROCERIES, etc.
    product_subcategory_l1: str       # L3: CHEESE, etc.
    product_subcategory_l2: str | None  # L4: EMMENTAL, etc.
    product_subcategory_l3: list[str] | None  # L5: ['UHT'], etc.
    needs_manual_review: bool | None  # Флаг ручной проверки
    
    # Метаданные позиции
    merchant: str | None
    store_address: str | None
    date: datetime | None

class ReceiptSums(BaseModel):
    total: float | None               # Итоговая сумма

class DataValidityInfo(BaseModel):
    sum_validation_passed: bool       # Прошла ли проверка суммы
    sum_difference: float | None      # Разница (если есть)

class ParseResultDTO(BaseModel):
    success: bool                     # Успешность
    items: list[ReceiptItem]          # Товары с категориями
    sums: ReceiptSums | None          # Суммы
    error: str | None                 # Ошибка (если есть)
    receipt_id: str | None            # ID чека
    data_validity: DataValidityInfo | None  # Валидация
    total_amount: float | None        # (deprecated)
```

---

## Почему такое решение

1. **Совместимость** - 1 в 1 с существующим finpi_parser_photo
2. **SRP** - D2 не знает о категориях, только о данных чека
3. **Чистый контракт** - D2 передает только то, за что отвечает
4. **Независимость** - D3 может менять структуру категорий без влияния на D2

---

## Последствия

1. **Файлы контрактов** в `contracts/`:
   - `d1_extraction_dto.py` - OCR результат
   - `d2_parsing_dto.py` - RawReceiptDTO (1:1 с finpi_parser_photo)
   - `d3_categorization_dto.py` - ParseResultDTO (1:1 с finpi_parser_photo)

2. **Immutable Contract** - внешние сервисы (Telegram, Frontend) зависят от структуры ParseResultDTO

3. **D2 не импортирует** ничего из D3

4. **Валидация** - D2 отвечает за checksum (sum_validation_passed), D3 за категоризацию
