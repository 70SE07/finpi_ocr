# Store Configs - Конфигурации магазинов

Конфигурации магазинов позволяют override параметры локали для конкретных магазинов.

## Структура

```
stores/
  ├── centershop.yaml  # Конфигурация для CenterShop
  ├── hit.yaml        # Конфигурация для HIT
  └── README.md       # Этот файл
```

## Использование

Конфигурации магазинов загружаются автоматически при парсинге, если указан `store_name`:

```python
# Загрузка конфигурации магазина
config = loader.load("de_DE", store_name="centershop")
```

## Примеры

### CenterShop

Override валюты - использует точку вместо запятой:

```yaml
currency:
  decimal_separads_separator: "."    # Разделитель тысяч
  symbol_position: "before"   # Позиция символа валюты
  format: "1.234,56"        # Формат числа
```

### Tax Override

```yaml
tax:
  inverted: true             # Инвертировать tax classes (A=19%, B=7%)
```

### Patterns Override

```yaml
patterns:
  total_keywords:
    - "gesamtbetrag"
    - "total"                # Добавляем дополнительные ключевые слова
  discount_keywords:
    - "rabatt"
  noise_keywords:
    - "tel."
```

### Extractors Override

```yaml
extractors:
  store_detection:
    scan_limit: 20           # Увеличить лимит сканирования
    known_brands:
      - "myshop"            # Добавить бренд
  semantic_extraction:
    fixers:
      - "custom_fixer"       # Добавить custom fixer
```
