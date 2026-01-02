# ADR-010: Иерархия конфигов Locale/Store

**Статус:** Утверждено  
**Вопросы плана:** Q3.1, Q3.2, Q3.3, Q3.4

---

## Контекст

Система должна обрабатывать чеки из 100+ локалей и 10,000+ вариаций магазинов.

Вопрос: как организовать конфигурацию для парсинга?

---

## Варианты

### Вариант A: locale/store иерархия с override (ВЫБРАН)

```
locales/
  de_DE/
    config.yaml           # базовый конфиг локали
    stores/
      centershop.yaml     # только исключения
```

### Вариант B: locale + отдельный stores/ справочник

```
locales/
  de_DE/config.yaml
stores/
  lidl.yaml
```

### Вариант C: Только locale

```
locales/
  de_DE/config.yaml       # все паттерны здесь
```

---

## Решение

**Вариант A: locale/store иерархия с override**

### Принципы

| Принцип | Описание |
|---------|----------|
| **Locale ОБЯЗАТЕЛЕН** | Каждый чек имеет локаль |
| **Store ОПЦИОНАЛЕН** | Нужен только если есть исключения из локали |
| **Наследование** | Store наследует все от locale |
| **Override** | Store переопределяет только отличия |
| **Привязка к локали** | Store config внутри locale (de_DE/stores/lidl.yaml) |

### Структура директорий

```
locales/
  de_DE/
    config.yaml              # базовый конфиг Германии
    stores/
      centershop.yaml        # исключение: точка вместо запятой
      hit.yaml               # исключение: категории на чеке, инверсия налогов
  pl_PL/
    config.yaml              # базовый конфиг Польши
    stores/
      zabka.yaml             # исключения Zabka (если есть)
```

### Пример конфигов

**de_DE/config.yaml (базовый):**
```yaml
locale:
  code: de_DE
  language: de
  region: DE

currency:
  symbol: "€"
  decimal_separator: ","
  thousands_separator: "."

tax:
  format: "suffix"           # A, B в конце строки
  classes: ["A", "B"]

date_formats:
  - "DD.MM.YYYY"
  - "DD.MM.YY"

patterns:
  total_keywords:
    - "summe"
    - "zu zahlen"
    - "gesamtbetrag"
```

**de_DE/stores/centershop.yaml (только исключения):**
```yaml
store:
  brand: "CenterShop"
  
# Override: только то что отличается от de_DE
currency:
  decimal_separator: "."     # точка вместо запятой
```

**de_DE/stores/hit.yaml (только исключения):**
```yaml
store:
  brand: "HIT"

tax:
  format: "inverted"         # B 19% вместо A 7%
  
features:
  has_store_categories: true # OBST & GEMÜSE, LEBENSMITTEL
```

### Логика применения

```python
def get_config(locale_code: str, store_name: str | None) -> Config:
    # 1. Загружаем базовый конфиг локали (ОБЯЗАТЕЛЬНО)
    base_config = load_locale_config(locale_code)
    
    # 2. Если store определен и есть конфиг - применяем override
    if store_name:
        store_config = load_store_config(locale_code, store_name)
        if store_config:
            return merge_configs(base_config, store_config)
    
    # 3. Иначе используем только locale config
    return base_config
```

---

## Q3.2: Store Detection = Акселератор

### Определение

Store detection - это **ОПЦИОНАЛЬНЫЙ** этап парсинга, который улучшает качество для известных магазинов с уникальными паттернами.

### Характеристики акселератора

| Аспект | Описание |
|--------|----------|
| **Обязателен?** | НЕТ. Система работает без него |
| **Fallback** | Всегда есть locale config |
| **Выгода** | Точнее парсинг для магазинов с исключениями |
| **Рост** | Расширяется по мере добавления store configs |

### Логика работы

```
Чек приходит в D2
    ↓
Locale определен (ОБЯЗАТЕЛЬНО)
    ↓
Попытка определить store (ОПЦИОНАЛЬНО)
    ↓
Store определен?
    ├── ДА → locale config + store override
    └── НЕТ → только locale config (работает!)
```

### Аналогия с D3

В D3 есть акселераторы (категоризаторы для известных магазинов/брендов), которые ускоряют и улучшают категоризацию.

В D2 store detection работает по тому же принципу - улучшает качество для известных случаев, но система работает и без него.

---

## Q3.3: Инвестиции в Store Configs

### Принцип: По мере необходимости

Store configs создаются **НЕ проактивно** для всех возможных магазинов, а **по мере выявления исключений**.

### Стратегия инвестиций

| Сценарий | Действие |
|----------|----------|
| Новый магазин, паттерны соответствуют locale | Ничего не делаем |
| Новый магазин, найдено исключение | Создаем store config с override |
| Известный магазин, новое исключение | Добавляем в существующий store config |

### Пример роста системы

```
Месяц 1: 5 локалей, 3 store configs (только исключения)
Месяц 3: 10 локалей, 8 store configs
Месяц 6: 20 локалей, 15 store configs
...
Год 2: 100 локалей, 50 store configs

Не 10,000 store configs! А только те, где есть исключения.
```

### Почему это системно

1. **Не тратим время** на создание configs для магазинов без исключений
2. **Добавляем по факту** когда встречаем реальную проблему
3. **Система живет** и развивается с реальными данными, не гипотетическими

---

## Почему это системное решение

### 1. Locale покрывает базовый случай

90% чеков обрабатываются только через locale config. Store config не нужен.

### 2. Исключения = конфиг, не код

```
НЕ ТАК:
  if store == "CenterShop":
      decimal_separator = "."

А ТАК:
  decimal_separator = config.currency.decimal_separator
  # значение берется из store или locale config
```

### 3. Масштабируется

```
Новая локаль:
  → Создаем ja_JP/config.yaml
  → Готово

Новый магазин с исключениями:
  → Создаем ja_JP/stores/xyz.yaml (только отличия)
  → Готово
```

### 4. Store привязан к локали

Lidl в Германии может отличаться от Lidl в Польше:
- `de_DE/stores/lidl.yaml`
- `pl_PL/stores/lidl.yaml`

---

## Что покрывается на каком уровне

| Паттерн | Уровень | Пример |
|---------|---------|--------|
| Язык | Locale | de, pl, es |
| Валюта | Locale | EUR, PLN |
| Десятичный разделитель (базовый) | Locale | de_DE = запятая |
| Десятичный разделитель (исключение) | Store | CenterShop = точка |
| Формат даты | Locale | DD.MM.YYYY |
| Формат налогов (базовый) | Locale | suffix (A, B) |
| Формат налогов (исключение) | Store | HIT = inverted |
| Pfand (залог) | Locale | de_DE (все магазины) |
| Категории на чеке | Store | HIT |
| SKU формат | Store | Aldi = 6 цифр |

---

## Связанные документы

- `docs/PROJECT_VISION.md` - принцип системности
- `docs/patterns/` - документация паттернов
- ADR-009 - гарантии качества D2

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2025-12-30 | Создан документ. Утвержден Вариант A (Q3.1). |
| 2025-12-31 | Добавлено: Q3.2 (Store Detection = Акселератор), Q3.3 (Инвестиции по мере необходимости). |
