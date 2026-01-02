# DTO Decisions - Обоснование Решений на Основе Паттернов


## Источник Данных

Все решения по структуре DTO основаны на анализе **53 чеков** из **10 локалей** и **19 магазинов**.  
Детальные паттерны: `docs/patterns/by_store/`

---

## ParsedReceiptItem DTO

```python
@dataclass
class ParsedReceiptItem:
    raw_name: str
    total_price: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    is_discount: bool = False
    tax_class: Optional[str] = None
    sku: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    raw_line: Optional[str] = None
    line_number: Optional[int] = None
    confidence: float = 1.0
```

---

## Обоснование Каждого Поля

### `raw_name: str` - ОБЯЗАТЕЛЬНО

**Почему обязательно:**
- Присутствует в 100% чеков всех локалей
- Критично для категоризации в Domain 3
- Должно быть ТОЧНОЙ копией с чека (не очищенной)

**Паттерны:**
- Может содержать налоговый префикс: `A_TORBA` (Carrefour pl_PL)
- Может быть обрезано: `Schweinenackenbraten` → `Schweinena...`
- Может быть на разных языках/скриптах: Thai, Cyrillic, Latin

**Решение:** Хранить как есть, без очистки.

---

### `total_price: float` - ОБЯЗАТЕЛЬНО

**Почему обязательно:**
- Присутствует в 100% чеков
- Необходимо для валидации суммы

**Паттерны десятичных разделителей:**
| Магазин | Разделитель | Пример |
|---------|-------------|--------|
| Lidl (de_DE) | `,` | `10,85` |
| CenterShop (de_DE) | `.` | `10.85` |
| Orlen (pl_PL) | `.` | `10.85` |
| 7-Eleven (th_TH) | `.` | `10.85` |

**Решение:** Парсить по магазину, хранить как float.

---

### `quantity: Optional[float] = None`

**Почему опционально:**
- Не всегда показано на чеке
- Может быть implicit (1 шт)

**Паттерны:**
| Локаль | Формат | Пример |
|--------|--------|--------|
| de_DE | `qty x price` | `2 x 4,29` |
| th_TH | `qty @ price` | `3 @ 37.00` |
| pl_PL | `qty*price=` | `0,694*9,99=` |
| bg_BG | Не показано | - |

**Решение:** `Optional[float]`, default `None`.

---

### `unit_price: Optional[float] = None`

**Почему опционально:**
- Показано только для qty > 1 или весовых товаров
- Может быть вычислено: `total_price / quantity`

**Решение:** `Optional[float]`, парсить если есть.

---

### `is_discount: bool = False`

**Почему обязательно:**
- Скидки есть в большинстве локалей
- Критично для правильного расчета суммы

**Паттерны ключевых слов:**
- de_DE: `Preisvorteil`, `RABATT`, `Rabattaktion`
- pl_PL: `Anulowano sprzedaż`
- pt_PT: `POUPANCA`
- bg_BG: `ОТСТ.`, `ОТСТЪПКА`
- th_TH: `ส่วนลดโปร`

**Решение:** `bool`, определять по ключевым словам + отрицательная цена.

---

### `tax_class: Optional[str] = None`

**Почему Optional[str]:**

| Формат | Примеры | Магазины |
|--------|---------|----------|
| Буква | A, B, C | Lidl, ALDI |
| Инвертированная | A=19%, B=7% | HIT, Penny |
| Цифра | 1, §1 | dm |
| Модификатор | +A, +B | Shell |
| Процент | %10, 19% | tr_TR, CenterShop |
| Кириллица | Я, *Б | uk_UA, bg_BG |
| Не показан | - | Consum (es_ES) |

**КРИТИЧНО:** A и B могут означать ПРОТИВОПОЛОЖНОЕ в разных магазинах!
- Lidl: A=7%, B=19%
- HIT: A=19%, B=7%

**Решение:** 
- `Optional[str]` - НЕ интерпретировать
- Передавать как есть в Domain 3
- Domain 3 решает как обрабатывать

---

### `sku: Optional[str] = None`

**Почему опционально:**
- Присутствует только в некоторых магазинах

**Паттерны:**
| Магазин | Формат | Пример |
|---------|--------|--------|
| ALDI | 4-6 цифр | `826945` |
| HIT | В скобках | `(399)` |
| Shell | Barcode | EAN |
| Hornbach | EAN-13 | `4013307334026` |
| Lidl | Нет | - |

**Решение:** `Optional[str]`, парсить если есть.

---

### `unit: Optional[str] = None`

**Почему опционально:**
- Не всегда показано
- Разные языки

**Паттерны:**
| Локаль | Единицы |
|--------|---------|
| de_DE | kg, Stk |
| pl_PL | kg, szt |
| uk_UA | шт, кг |
| cs_CZ | Kus, Pár, kg |
| th_TH | - |

**Решение:** `Optional[str]`, хранить как есть.

---

### `category: Optional[str] = None`

**Почему опционально:**
- Только 2 магазина печатают категории:
  - HIT (de_DE): `THEKE/SBHF`, `LEBENSMITTEL`, `GETRÄNKE`
  - Continente (pt_PT): `Frutas e Legumes`

**Решение:** `Optional[str]`, использовать для пре-категоризации если есть.

---

### `raw_line: Optional[str] = None`

**Почему рекомендовано:**
- Для отладки
- Для повторного анализа
- Для ML обучения

**Решение:** Хранить оригинальную строку(и) с чека.

---

### `line_number: Optional[int] = None`

**Почему опционально:**
- Полезно для отладки
- Помогает при мультилинейных товарах

**Решение:** `Optional[int]`, номер первой строки товара.

---

### `confidence: float = 1.0`

**Почему рекомендовано:**
- Для фильтрации ненадежных результатов
- Для приоритизации ручной проверки

**Решение:** `float` от 0.0 до 1.0.

---

## Решения НЕ Включать

### `weight_kg` - НЕ отдельное поле
**Причина:** Можно вычислить из `quantity` + `unit='kg'`

### `discount_amount` - НЕ отдельное поле
**Причина:** `is_discount=True` + отрицательный `total_price` достаточно

### `tax_rate_percent` - НЕ включаем
**Причина:** Невозможно надежно определить (инверсия A/B)

---

## Связь с Ground Truth

Каждый файл в `docs/ground_truth/` содержит поле `items` в формате, совместимом с этим DTO:

```json
{
  "items": [
    {
      "raw_name": "Schweinenackenbraten",
      "qty": 1,
      "unit_price": 8.99,
      "total_price": 10.85,
      "tax_class": "A",
      "weight_kg": 1.207
    }
  ]
}
```

**Трансформация:** `qty` → `quantity`, `weight_kg` вычисляется из контекста.
