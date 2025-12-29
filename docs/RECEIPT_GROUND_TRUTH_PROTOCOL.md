# Протокол создания Ground Truth для нового чека

**Назначение:** Пошаговая инструкция для AI при получении нового изображения чека.

---

## ВХОДНЫЕ ДАННЫЕ

- Изображение чека (jpeg/png)
- Путь к изображению (опционально)

---

## ШАГ 1: Визуальный анализ

Посмотри на изображение и определи:

| Параметр | Как определить |
|----------|----------------|
| **Локаль** | Язык текста, валюта, формат даты |
| **Магазин** | Логотип, название в шапке |
| **Дата/время** | Обычно в шапке или подвале |
| **Итоговая сумма** | Ключевые слова: Summe, Total, SUMA, Итого |
| **Способ оплаты** | Karte, Bar, Cash, Картой |

---

## ШАГ 2: Определение ID

Выполни команду:
```bash
ls docs/ground_truth/*.json | wc -l
```

**Новый ID** = количество файлов + 1 (с ведущими нулями: 001, 054, 100)

---

## ШАГ 3: Создание Ground Truth файла

**Путь:** `docs/ground_truth/{ID}_{locale}_{store}_{image_name}.json`

**Пример:** `054_de_DE_lidl_IMG_1234.json`

**Формат файла:**

```json
{
  "id": "054",
  "source_file": "photo/GOODS/Lidl/IMG_1234.jpeg",
  "locale": "de_DE",
  "store": {
    "name": "Lidl",
    "address": "Steinhauser Auel 1, 51491 Overath-Vilkerath"
  },
  "metadata": {
    "date": "2025-01-15",
    "time": "14:30",
    "receipt_total": 45.67,
    "currency": "EUR",
    "payment_method": "Karte (girocard)",
    "tax_block": {
      "A": {"rate": "7%", "netto": 30.00, "mwst": 2.10, "brutto": 32.10},
      "B": {"rate": "19%", "netto": 11.40, "mwst": 2.17, "brutto": 13.57}
    }
  },
  "items": [
    {"raw_name": "Butter 250g", "quantity": 2, "unit_price": 1.85, "total_price": 3.70, "tax_class": "A"},
    {"raw_name": "Mineralwasser 6x1.5L", "quantity": null, "unit_price": null, "total_price": 2.34, "tax_class": "B"},
    {"raw_name": "Pfand", "quantity": null, "unit_price": null, "total_price": 1.50, "tax_class": "M", "is_pfand": true},
    {"raw_name": "Preisvorteil", "quantity": null, "unit_price": null, "total_price": -0.50, "tax_class": "A", "is_discount": true}
  ],
  "validation": {
    "checksum_method": "SUM(items) == receipt_total",
    "items_sum": 45.67,
    "expected_total": 45.67,
    "discrepancy": 0.00
  },
  "notes": [
    "Особенность 1",
    "Особенность 2"
  ]
}
```

### Обязательные поля items:

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `raw_name` | str | ДА | Точная строка с чека |
| `total_price` | float | ДА | Итоговая цена позиции |
| `quantity` | float/null | НЕТ | Количество (null если не указано) |
| `unit` | str/null | НЕТ | Единица измерения (kg, шт, Kus) |
| `unit_price` | float/null | НЕТ | Цена за единицу |
| `tax_class` | str | НЕТ | Налоговый класс как есть (A, B, 1, *Б, Я, %10) |
| `is_discount` | bool | НЕТ | true если это скидка |
| `is_pfand` | bool | НЕТ | true если это залог за тару (только de_DE) |
| `is_fresh` | bool | НЕТ | true если с прилавка свежих продуктов (HIT) |
| `category` | str | НЕТ | Категория с чека (HIT, Continente) |
| `discount_label` | str | НЕТ | Метка скидки ("*** Discount Preis ***") |
| `note` | str | НЕТ | Примечание к позиции ("* nicht rabattfähig") |

### Правила заполнения:

1. **raw_name** - копировать ТОЧНО как на чеке, включая сокращения
2. **total_price** - всегда float, скидки с минусом (-0.50)
3. **quantity** - `null` если не указано явно на чеке (НЕ опускать поле!)
4. **tax_class** - копировать как строку, НЕ интерпретировать
5. **is_pfand** - только для немецких чеков с залогом за бутылки

### Дополнительные поля metadata (опционально):

| Поле | Когда использовать |
|------|-------------------|
| `currency_symbol` | Если отличается от кода (лв., ₹) |
| `receipt_total_eur` | Для двойной валюты (bg_BG) |
| `eur_rate` | Курс обмена |
| `cash_given` | Если оплата наличными |
| `change` | Сдача |
| `total_savings` | Общая экономия (#ТИ СПЕСТИ#) |
| `items_count` | Количество позиций на чеке |
| `receipt_number` | Номер чека |
| `transaction_number` | Номер транзакции |

### Дополнительные поля store (опционально):

| Поле | Когда использовать |
|------|-------------------|
| `brand` | Если отличается от name (LIDL & Cia → Lidl) |
| `branch` | Номер/название филиала |
| `code` | Код магазина (HIT 033 Overath) |
| `hours` | Часы работы |
| `ust_id` | Немецкий налоговый ID |
| `legal_name` | Полное юридическое название |
| `eik` | Болгарский налоговый ID |
| `zdds` | Болгарский VAT ID |
| `nif` | Испанский/Португальский налоговый ID |
| `type` | Тип магазина (Hardware store, Supermarket) |

---

## ШАГ 4: Валидация

**КРИТИЧНО:** Выполни проверку перед сохранением:

```
SUM(items.total_price) == metadata.receipt_total
```

**discrepancy ДОЛЖЕН быть 0.00**

Если не сходится:
1. Перепроверь все позиции
2. Проверь скидки (отрицательные цены)
3. Проверь весовые товары
4. Проверь Pfand/залог

---

## ШАГ 5: Обновление паттернов магазина

**Путь:** `docs/patterns/by_store/{locale}/{store}.json`

### Если магазин НОВЫЙ:

Создай файл по шаблону:

```json
{
  "store": {
    "brand": "StoreName",
    "type": "Supermarket",
    "locale": "xx_XX"
  },
  "sources": {
    "receipt_ids": ["054"],
    "total_receipts": 1
  },
  "patterns": {
    "number_format": {
      "decimal_separator": ",",
      "thousands_separator": "."
    },
    "tax_class": {
      "format": "single_letter",
      "values": ["A", "B"],
      "inverted": false
    },
    "item_line": {
      "format": "описание формата"
    }
  },
  "notes": []
}
```

### Если магазин СУЩЕСТВУЕТ:

1. Добавь ID в `sources.receipt_ids`
2. Увеличь `sources.total_receipts`
3. Добавь новые паттерны если обнаружены

---

## ШАГ 6: Обновление индекса локали

**Путь:** `docs/patterns/by_store/{locale}/_index.json`

Обнови поле `total_receipts` для локали и магазина.

---

## ШАГ 7: Обновление MATRIX.json

**Путь:** `docs/patterns/MATRIX.json`

Обнови:
- `total_receipts_analyzed`
- `locales.{locale}.receipts`

---

## КОНТРОЛЬНЫЙ ЧЕКЛИСТ

Перед завершением проверь:

- [ ] Ground Truth файл создан с правильным именем
- [ ] Все items заполнены корректно
- [ ] `validation.discrepancy` = 0.00
- [ ] Паттерны магазина обновлены/созданы
- [ ] `_index.json` локали обновлен
- [ ] `MATRIX.json` обновлен

---

## СПРАВОЧНИК ЛОКАЛЕЙ

| Локаль | Страна | Десятичный | Валюта |
|--------|--------|------------|--------|
| de_DE | Германия | , | EUR |
| pl_PL | Польша | , или . | PLN |
| es_ES | Испания | , | EUR |
| pt_PT | Португалия | , | EUR |
| th_TH | Таиланд | . | THB |
| uk_UA | Украина | , | UAH |
| cs_CZ | Чехия | , | CZK |
| bg_BG | Болгария | . | BGN |
| tr_TR | Турция | , | TRY |
| en_IN | Индия | . | INR |

---

## КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ

1. **Десятичный разделитель** - НЕ определять по локали! Смотри на чек (CenterShop de_DE использует точку!)

2. **Tax class инверсия** - HIT и Penny: A=19%, B=7% (инвертировано!)

3. **Многострочные товары** - uk_UA, cs_CZ имеют товары на 2-3 строках

4. **Буддийский календарь** - th_TH: год - 543 = григорианский

5. **Количество в начале строки** - th_TH: `3 ข้าว @ 37.00`
