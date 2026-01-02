# Анализ локалей (Locales Analysis) - ФИНАЛЬНАЯ ВЕРСИЯ

База знаний по форматам чеков из разных стран и магазинов.

## Статистика

| Метрика | Значение |
|---------|----------|
| **Локали** | 11 |
| **Магазины** | 28 |
| **Чеки проанализировано** | 53 |
| **Checksum 0.00** | 100% |

> Детальная матрица паттернов: [patterns/MATRIX.md](../patterns/MATRIX.md)

## Структура

```
locales_analysis/
├── {locale_code}/           # Например: de_DE, pl_PL, bg_BG
│   ├── _overview.md         # Общие паттерны страны
│   └── {store}.md           # Анализ конкретного магазина
```

## Проанализированные локали

| Локаль | Страна | Магазины | Чеков |
|--------|--------|----------|-------|
| [de_DE](de_DE/_overview.md) | Германия | Lidl, ALDI, Netto, Penny, EDEKA, HIT, dm, Shell, CenterShop, Bäckerei Müller, Kleins Backstube | **15+** |
| [pl_PL](pl_PL/_overview.md) | Польша | Carrefour, Cropp, Orlen | **7** |
| [es_ES](es_ES/_overview.md) | Испания | Consum | **2** |
| [bg_BG](bg_BG/_overview.md) | Болгария | Billa | 1 |
| [cs_CZ](cs_CZ/_overview.md) | Чехия | Hornbach | 1 (проблемный) |
| [tr_TR](tr_TR/_overview.md) | Турция | F33 ENVA | 1 |
| [en_IN](en_IN/_overview.md) | Индия | NY Burrito Company | 1 |
| [th_TH](th_TH/_overview.md) | Таиланд | 7-Eleven | 1 |
| [pt_PT](pt_PT/_overview.md) | Португалия | Continente | 1 |
| [uk_UA](uk_UA/_overview.md) | Украина | Dnipro-M | 1 |

## Критические находки

### 1. Десятичный разделитель - НЕ ФИКСИРОВАН!

| Страна | Магазины с запятой | Магазины с точкой |
|--------|-------------------|-------------------|
| Германия | Lidl, ALDI, dm, EDEKA... | **CenterShop** |
| Польша | Carrefour, Cropp | **Orlen** |

### 2. Tax class инверсия

| Магазин | A | B |
|---------|---|---|
| Lidl, ALDI, EDEKA | 7% | 19% |
| **HIT, Penny** | **19%** | **7%** |

### 3. Множество форматов Pfand

| Магазин | Формат |
|---------|--------|
| Lidl | M |
| ALDI | B |
| EDEKA | +B |
| dm | §1 |
| HIT | A* |
| CenterShop | *0.25 |

### 4. Категории на чеке - только HIT

```
LEBENSMITTEL
GEKÜHLTE LEBENSMITTEL
TIEFKÜHLKOST
GETRÄNKE
NON FOOD
PFAND/LEERGUT
```

### 5. Скидки в процентах - только ALDI

```
733244 F&G Häh Min.schn           5,49 A
Rabatt      30,0%                -1,65
```

### 6. Округление валюты - Чехия

```
SOUČET: 1135,78 CZK
Zaokrouhlení: +0,22 CZK
K zaplacení: 1136,00 CZK
```

## Сводная таблица по странам

| Локаль | Валюта | Дес. разд. | Tax block | Особенность |
|--------|--------|------------|-----------|-------------|
| de_DE | EUR | , или . | Да | Инверсия tax, категории |
| pl_PL | PLN | , или . | Да | Префиксы A_/C_ |
| es_ES | EUR | , | Да (IVA) | 3 ставки IVA |
| bg_BG | BGN | . | Нет | Кириллица, *Б |
| cs_CZ | CZK | , | Да | Zaokrouhlení |
| tr_TR | TRY | , | Нет | %налог в строке |
| en_IN | INR | . | GST | CGST+SGST |
| th_TH | THB | . | Нет | Тайский скрипт |
| pt_PT | EUR | , | Да | Категории товаров |
| uk_UA | UAH | пробел | Нет | Многострочный |

## Финальный DTO (подтвержден)

```python
@dataclass
class ParsedReceiptItem:
    # ОБЯЗАТЕЛЬНЫЕ (100%)
    raw_name: str
    total_price: float
    
    # ВАЖНЫЕ (70-80%)
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    is_discount: bool = False
    tax_class: Optional[str] = None
    
    # ОПЦИОНАЛЬНЫЕ
    sku: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None  # HIT only
```

## Валидация (100% успех)

```
SUM(items.total_price) == receipt_total
```

**Работает на ВСЕХ 36+ чеках с расхождением 0.00**

## Связанные документы

- **[Матрица паттернов (MATRIX.md)](../patterns/MATRIX.md)** - системный обзор всех паттернов
- **[Матрица паттернов (MATRIX.json)](../patterns/MATRIX.json)** - машиночитаемая версия для AI
- **[Решения по DTO](../patterns/dto_decisions.md)** - обоснование структуры DTO
- [Исследование DTO товарной позиции](../contracts/item_dto_research.md)
- [Исследование правил валидации](../contracts/validation_rules_research.md)
