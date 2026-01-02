# ADR-003: Стабильность контракта RawOCRResult

**Статус:** Принято (обновлено 31.12.2024)  
**Вопрос плана:** Q1.3

---

## Контекст

`RawOCRResult` - контракт между D1 (Extraction) и D2 (Parsing).

Проблема: формат зависит от Google Vision API, который мы не контролируем.

---

## Вопрос

Как обеспечить стабильность контракта `RawOCRResult`?

---

## Решение

### 1. Наша схема стабильна

Файл `contracts/d1_extraction_dto.py` определяет НАШУ схему (Pydantic):

```python
class RawOCRResult(BaseModel):
    full_text: str = ""                    # Полный текст (для regex, паттернов)
    words: List[Word] = []                 # Слова с координатами (для layout)
    metadata: Optional[OCRMetadata] = None # Метаданные обработки
```

**Правила изменения:**
- Поля НЕ удаляем и НЕ переименовываем
- Новые поля можно добавлять (backward compatible)
- Обязательные поля: `full_text`, `words`

### 2. Адаптер в Infrastructure

Если Google Vision изменит формат:
- Меняем адаптер `GoogleVisionOCR._parse_response()`
- Parsing домен не затрагивается
- Контракт остается стабильным

### 3. Parsing работает с нашей схемой

Parsing домен:
- Получает `RawOCRResult` (наша схема)
- Не знает о Google Vision
- Работает с `full_text` и `words[]`

---

## Структура RawOCRResult (ADR-006)

```json
{
  "full_text": "Весь текст чека одной строкой",
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
    "source_file": "IMG_1336",
    "image_width": 800,
    "image_height": 1200,
    "processed_at": "2024-12-31T10:00:00",
    "preprocessing_applied": ["grayscale", "deskew"]
  }
}
```

**Почему `words[]` вместо `blocks[]`:** См. ADR-006 — слова с координатами позволяют D2 группировать их в строки и понимать layout.

---

## Последствия

1. **Стабильность** - Parsing домен защищен от изменений Google Vision
2. **Гибкость** - можно заменить OCR провайдера (GPT-4 Vision и др.)
3. **Тестируемость** - можно тестировать Parsing с mock данными
4. **Валидация** - Pydantic гарантирует корректность данных

---

## Связанные решения

- [ADR-006: D1→D2 Contract Design](006_d1_d2_contract_design.md) — почему `words[]`