# Pattern Matrix - Агрегированный Анализ Паттернов

**Проанализировано чеков:** 55  
**Локалей:** 10  
**Магазинов:** 21

## Структура Документации

```
docs/patterns/
├── MATRIX.json          # Глобальная агрегация (machine-readable)
├── MATRIX.md            # Этот файл (human-readable)
├── dto_decisions.md     # Обоснование решений по DTO
└── by_store/            # Детальные паттерны по магазинам
    ├── de_DE/
    │   ├── _index.json  # Индекс локали
    │   ├── lidl.json    # 18 чеков
    │   ├── aldi.json    # 2 чека
    │   ├── hit.json     # 4 чека (INVERTED tax!)
    │   ├── edeka.json   # 4 чека
    │   ├── penny.json   # 1 чек (INVERTED tax!)
    │   ├── netto.json   # 1 чек
    │   ├── dm.json      # 2 чека (numeric tax)
    │   ├── shell.json   # 1 чек (+A/+B tax)
    │   ├── centershop.json  # 1 чек (DOT decimal!)
    │   ├── baeckerei.json   # 1 чек (#xxx SKU)
    │   └── kleins-backstube.json  # 1 чек (timestamp per item)
    ├── pl_PL/
    │   ├── _index.json
    │   ├── carrefour.json  # 5 чеков (A_prefix)
    │   ├── cropp.json      # 1 чек
    │   ├── orlen.json      # 1 чек (DOT decimal!)
    │   └── zabka.json      # 1 чек (ISO date, suffix tax)
    ├── es_ES/
    │   ├── _index.json
    │   ├── consum.json     # 2 чека
    │   └── mercadona.json  # 1 чек (no tax in line!)
    ├── pt_PT/
    │   ├── _index.json
    │   ├── lidl.json       # 1 чек
    │   └── continente.json # 1 чек (categories!)
    ├── th_TH/
    │   ├── _index.json
    │   └── 7-eleven.json   # 1 чек (Buddhist calendar!)
    ├── uk_UA/
    │   ├── _index.json
    │   └── dnipro-m.json   # 1 чек (multiline items!)
    ├── cs_CZ/
    │   ├── _index.json
    │   └── hornbach.json   # 1 чек (3-line items, rounding!)
    ├── bg_BG/
    │   ├── _index.json
    │   └── billa.json      # 1 чек (*Б tax, dual currency)
    ├── tr_TR/
    │   ├── _index.json
    │   └── f33-enva.json   # 1 чек (*price, %tax)
    └── en_IN/
        ├── _index.json
        └── nybc.json       # 1 чек (GST split)
```

---

## КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ

### 1. Десятичный Разделитель
| Локаль | Стандарт | Исключения |
|--------|----------|------------|
| de_DE | `,` | CenterShop использует `.` |
| pl_PL | `,` | Orlen использует `.` |
| bg_BG | `.` | - |
| en_IN | `.` | - |
| th_TH | `.` | - |

**ВЫВОД:** Нельзя определить разделитель только по локали!

### 2. Налоговый Класс (tax_class)
| Формат | Примеры | Магазины |
|--------|---------|----------|
| Одна буква | A, B, C, F, M | Lidl, ALDI, Netto |
| Инвертированный | A=19%, B=7% | HIT, Penny |
| Цифровой | 1, §1 | dm |
| С модификатором | +A, +B, AW | Shell, EDEKA |
| Процент | %10, %18, 19% | CenterShop, tr_TR |
| Кириллица | Я, *Б | uk_UA, bg_BG |
| Префикс в имени | A_TORBA | Carrefour (pl_PL) |
| Суффикс после цены | 4,99A | Zabka (pl_PL) |
| Не показан | - | Consum, Mercadona (es_ES) |

**ВЫВОД:** `tax_class` ДОЛЖЕН быть `Optional[str]` - слишком много вариаций!

### 3. Многострочные Товары
| Локаль | Строк на товар | Пример |
|--------|----------------|--------|
| uk_UA | 2 | Имя / qty x price |
| cs_CZ | 3 | EAN / Имя / qty x price |

### 4. Позиция Количества
| Локаль | Позиция | Пример |
|--------|---------|--------|
| de_DE, pl_PL, es_ES | После имени | `Butter x 2` |
| th_TH | В начале строки | `2 Butter` |

### 5. Календарная Система
| Локаль | Система | Смещение |
|--------|---------|----------|
| th_TH | Буддийский | -543 |
| Все остальные | Григорианский | 0 |

---

## Паттерны Скидок

| Локаль | Ключевые слова |
|--------|----------------|
| de_DE | Preisvorteil, RABATT, Rabatt, Rabattaktion |
| pl_PL | Anulowano sprzedaż |
| pt_PT | POUPANCA |
| bg_BG | ОТСТ., ОТСТЪПКА |
| th_TH | ส่วนลดโปร, ส่วนลดสมาชิก |

---

## Уникальные Особенности

| Магазин | Особенность | Значение |
|---------|-------------|----------|
| HIT (de_DE) | Категории на чеке | Пре-категоризация |
| Continente (pt_PT) | Категории на чеке | Пре-категоризация |
| ALDI (de_DE) | SKU перед именем | 4-6 цифр |
| HIT (de_DE) | SKU в скобках | (399) |
| Kleins (de_DE) | Время на каждый товар | HH:MM |
| Hornbach (cs_CZ) | Zaokrouhlení | Округление к целым CZK |
| Billa (bg_BG) | Двойная валюта | BGN + EUR |
| Mercadona (es_ES) | Налог только в блоке IVA | 4%/10%/21% |
| Zabka (pl_PL) | ISO формат даты | YYYY-MM-DD |
| Zabka (pl_PL) | Франшиза | Владелец в header |

---

## Импликации для DTO

```python
@dataclass
class ParsedReceiptItem:
    raw_name: str           # ОБЯЗАТЕЛЬНО - точная строка с чека
    total_price: float      # ОБЯЗАТЕЛЬНО - итоговая цена позиции
    quantity: Optional[float] = None    # Не всегда показано
    unit_price: Optional[float] = None  # Не всегда показано
    is_discount: bool = False           # ОБЯЗАТЕЛЬНО
    tax_class: Optional[str] = None     # str! Слишком много вариаций
    sku: Optional[str] = None           # Зависит от магазина
    unit: Optional[str] = None          # шт, Kus, kg, etc.
    category: Optional[str] = None      # Только HIT, Continente
    raw_line: Optional[str] = None      # Для отладки
```

---

## Критические Правила Парсинга

1. **НЕ** предполагать десятичный разделитель по локали - проверять по магазину
2. **НЕ** интерпретировать процент налогового класса - передавать как строку
3. **Обрабатывать** многострочные товары (uk_UA, cs_CZ)
4. **Обрабатывать** количество в начале строки (th_TH)
5. **Конвертировать** буддийские даты (th_TH)
6. **Обрабатывать** округление (cs_CZ - Zaokrouhlení)
7. **Помнить:** A/B могут быть инвертированы (HIT, Penny)

---

## Статистика по Локалям

| Локаль | Чеков | Магазинов | Валюта |
|--------|-------|-----------|--------|
| de_DE | 36 | 11 | EUR |
| pl_PL | 8 | 4 | PLN |
| es_ES | 3 | 2 | EUR |
| pt_PT | 2 | 2 | EUR |
| th_TH | 1 | 1 | THB |
| uk_UA | 1 | 1 | UAH |
| cs_CZ | 1 | 1 | CZK |
| bg_BG | 1 | 1 | BGN |
| tr_TR | 1 | 1 | TRY |
| en_IN | 1 | 1 | INR |
| **ИТОГО** | **55** | **21** | **8 валют** |
