# ADR-003: Стабильность контракта RawOCRResult

**Статус:** Принято  
**Дата:** 2025-12-29  
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

Файл `contracts/raw_ocr_schema.py` определяет НАШУ схему:

```python
@dataclass
class RawOCRResult:
    full_text: str                    # Обязательно
    blocks: List[TextBlock]           # Обязательно
    raw_annotations: List[RawAnnotation]  # Опционально
    metadata: Optional[OCRMetadata]   # Опционально
```

**Правила изменения:**
- Поля НЕ удаляем и НЕ переименовываем
- Новые поля можно добавлять (backward compatible)
- Обязательные поля: `full_text`, `blocks`

### 2. Адаптер в Infrastructure

Если Google Vision изменит формат:
- Меняем адаптер `GoogleVisionOCRAdapter`
- Parsing домен не затрагивается
- Контракт остается стабильным

### 3. Parsing работает с нашей схемой

Parsing домен:
- Получает `RawOCRResult` (наша схема)
- Не знает о Google Vision
- Работает с `full_text` и `blocks`

---

## Структура RawOCRResult

```json
{
  "full_text": "Весь текст чека одной строкой",
  "blocks": [
    {
      "text": "Название товара",
      "confidence": 0.98,
      "bounding_box": {"x": 100, "y": 200, "width": 300, "height": 30},
      "block_type": "PARAGRAPH"
    }
  ],
  "metadata": {
    "timestamp": "2025-12-29T10:00:00",
    "source_file": "IMG_1336"
  }
}
```

---

## Последствия

1. **Стабильность** - Parsing домен защищен от изменений Google Vision
2. **Гибкость** - можно заменить OCR провайдера (GPT-4 Vision и др.)
3. **Тестируемость** - можно тестировать Parsing с mock данными
