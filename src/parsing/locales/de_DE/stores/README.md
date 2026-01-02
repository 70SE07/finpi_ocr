# Store Configs - Конфигурации магазинов

Конфигурации магазинов позволяют:
1. **Детекцию магазина** (Stage 3) - brands/aliases для поиска в тексте чека
2. **Override параметров локали** - специфичные настройки парсинга

## Структура YAML

```yaml
# === STAGE 3: STORE DETECTION ===
detection:
  brands:           # Слова для поиска в тексте чека (обязательно)
    - lidl
    - lidl plus
  aliases:          # Дополнительные варианты написания
    - LIDL STIFTUNG
    - LIDL DIENSTLEISTUNG
  priority: 1       # Приоритет при конфликтах (выше = важнее)

# === PARSING OVERRIDES (опционально) ===
total_keywords:     # Override ключевых слов итоговой суммы
  - "$replace"      # $replace = полная замена списка локали
  - summe
  - zahlbetrag

skip_keywords:      # Расширение списка skip-слов
  - "pfandrecht"
  - "ohne gewähr"

line_split_y_threshold: 8  # Y-порог для разделения строк
```

## Файлы магазинов

| Файл | Магазин | Brands |
|------|---------|--------|
| aldi.yaml | ALDI | aldi, aldi süd, aldi nord |
| lidl.yaml | LIDL | lidl, lidl plus |
| rewe.yaml | REWE | rewe |
| edeka.yaml | EDEKA | edeka |
| kaufland.yaml | Kaufland | kaufland |
| penny.yaml | Penny | penny, penny markt |
| netto.yaml | Netto | netto |
| dm.yaml | dm-drogerie | dm, dm-drogerie |
| rossmann.yaml | Rossmann | rossmann |
| ... | ... | ... |

## Использование

### Детекция магазина (автоматически)

Stage 3 автоматически загружает все stores/*.yaml и ищет brands/aliases в тексте чека:

```python
from src.parsing.stages.pipeline import ParsingPipeline

pipeline = ParsingPipeline()
result = pipeline.process(raw_ocr)

print(result.store.store_name)  # "lidl"
print(result.store.confidence)  # 1.0
```

### Загрузка конфигурации магазина

```python
from src.parsing.locales.config_loader import LocaleConfig

# Загрузка с override настроек магазина
config = LocaleConfig.load("de_DE", store_name="aldi")

# Теперь config содержит merged настройки локали + магазина
print(config.total_keywords)  # ["summe", "zahlbetrag", "betrag"]
```

## Добавление нового магазина

1. Создайте файл `stores/{name}.yaml`
2. Добавьте секцию `detection` с brands
3. (Опционально) Добавьте override настройки парсинга

**Пример:**

```yaml
# stores/kaufhaus.yaml
detection:
  brands:
    - kaufhaus
    - kaufhaus center
  aliases:
    - KAUFHAUS GMBH
  priority: 1

# Специфичные настройки (опционально)
total_keywords:
  - "$replace"
  - summe
  - gesamtbetrag
```

## Принципы

- **0 хардкода в Python** - все магазины загружаются из YAML
- **Новый магазин = новый YAML файл** - без изменения кода
- **Наследование** - магазин наследует настройки локали и может override
- **Приоритеты** - при конфликтах побеждает магазин с высшим priority
