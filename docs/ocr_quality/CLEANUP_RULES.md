# Правила очистки для s1_ocr_cleanup

Документ определяет правила для реализации модуля OCR Cleanup на основе анализа артефактов.

---

## Обзор

На основе анализа 1 чека (de_DE, Lidl, IMG_1292) выявлено 9 артефактов.

| Тип артефакта | Количество | Процент | Приоритет |
|----------------|-----------|--------|-----------|
| CHAR_MISS | 3 | 33.3% | ВЫСОКИЙ |
| CHAR_SUB | 2 | 22.2% | ВЫСОКИЙ |
| DIAC_LOSS | 1 | 11.1% | СРЕДНИЙ |
| WORD_SPLIT | 1 | 11.1% | СРЕДНИЙ |
| GARBAGE | 1 | 11.1% | СРЕДНИЙ |

**Вывод:** Наибольшую проблему составляют пропуски символов (33.3%) и замены символов (22.2%).

---

## Архитектура модулей

Согласно утверждённому подходу (folder = modules), s1_ocr_cleanup должен содержать:

```
src/parsing/s1_ocr_cleanup/
├── __init__.py
├── stage.py              # Оркестратор
├── char_replacer.py     # CHAR_SUB, CHAR_MISS, CHAR_EXTRA
├── word_merger.py      # WORD_SPLIT, WORD_MERGE
├── garbage_filter.py     # GARBAGE
├── diacritics_restorer.py # DIAC_LOSS
├── unicode_normalizer.py # Unicode нормализация
└── rules_loader.py      # Загрузка правил из YAML
```

---

## Правила по типам артефактов

### 1. Character Replacement (CHAR_SUB, CHAR_MISS, CHAR_EXTRA)

**Ответственный модуль:** `char_replacer.py`

#### Правило 1: Контекстная замена в заголовке

**ID:** `de_DE_header_press`

**Тип:** `CHAR_SUB`

**Паттерн:** `^rebe$` в начале чека (header)

**Замена:** `PRESS`

**Уверенность:** 0.90

**Применение:** Только если предыдущая строка содержит магазин

**Пример:**
```python
# Было
"rebe\nSteinhauser Auel 1\n..."

# Стало
"PRESS\nSteinhauser Auel 1\n..."
```

#### Правило 2: Словарная коррекция немецких слов

**ID:** `de_DE_dict_correction`

**Тип:** `CHAR_SUB`

**Паттерн:** Словарь немецких слов → OCR вариант

**Уверенность:** 0.95

**Примеры:**
```python
GERMAN_DICT = {
    "Olivenole": "Olivenöl",
    "Feink": "Feink",
    # ... другие слова
}
```

**Логика:**
1. Найти слово в словаре
2. Если найдено → заменить
3. Сохранить оригинальную структуру (заглавные/строчные)

#### Правило 3: Восстановление пропущенных символов

**ID:** `de_DE_restore_missing_n`

**Тип:** `CHAR_MISS`

**Паттерн:** `Schweinenacken` → `Schweinenacken`

**Замена:** Добавить `n` после `Schweine`

**Уверенность:** 0.85

**Логика:**
```python
def restore_missing_char(word: str) -> str:
    # Общие шаблоны пропусков для немецкого
    patterns = [
        (r"Schweine(acken)$", r"Schweinen\1aken"),
        (r"Hähn(\\.Keulen)$", r"Hähnchen\\1keulen"),
        # ... другие паттерны
    ]

    for pattern, replacement in patterns:
        if re.match(pattern, word):
            return word.replace("acken", "acken")

    return word
```

#### Правило 4: Исправление опечаток в середине слова

**ID:** `de_DE_fix_middle_char`

**Тип:** `CHAR_SUB`

**Паттерн:** `Feink` → `Feink`

**Замена:** Заменить `k` на `k` в словах с `e` и `ink` суффиксом

**Уверенность:** 0.85

**Пример:**
```python
# Было: Bull'sEyeFeink
# Стало: Bull'sEyeFeink
```

---

### 2. Word Merging (WORD_SPLIT, WORD_MERGE)

**Ответственный модуль:** `word_merger.py`

#### Правило 5: Разделение склеенных слов

**ID:** `de_DE_split_on_period`

**Тип:** `GARBAGE` / `WORD_MERGE`

**Паттерн:** `Word1\.Word2` → `Word1 Word2`

**Замена:** Заменить точку на пробел

**Уверенность:** 0.95

**Логика:**
```python
def split_merged_words(text: str) -> str:
    # Паттерны для склеенных слов
    patterns = [
        r"([A-Za-zäöüß])\.([A-Z][a-zäöüß])",  # Title.Word
        r"([A-Za-zäöüß]+)\.([A-Z][A-Za-zäöüß]+)"  # Word.Word
    ]

    result = text
    for pattern in patterns:
        result = re.sub(pattern, r"\1 \2", result)

    return result
```

**Пример:**
```python
# Было: Bull'sEyeFeink.Honey
# Стало: Bull'sEyeFeink Honey
```

#### Правило 6: Визуальная проверка разделений

**ID:** `visual_split_verification`

**Тип:** `WORD_SPLIT`

**Паттерн:** `Word1 Word2` → проверить визуально

**Замена:** Оставить как есть, но пометить для ручной проверки

**Уверенность:** 0.70

**Логика:**
- Если слово `Baguettes Knoblauch` не найдено в словаре
- Пометить как `needs_visual_verification`
- Не выполнять автоматическое разделение

---

### 3. Diacritics Restoration (DIAC_LOSS)

**Ответственный модуль:** `diacritics_restorer.py`

#### Правило 7: Восстановление диакритики по словарю

**ID:** `de_DE_restore_diacritics`

**Тип:** `DIAC_LOSS`

**Паттерн:** `rose` → `rosé` (в конце слова перед ценой)

**Замена:** Добавить `é` вместо `e`

**Уверенность:** 0.90

**Логика:**
```python
def restore_diacritics(text: str, locale: str) -> str:
    # Контекст: слово перед ценой (регулярное выражение цены)
    price_pattern = r"\d+[,\.]\d{2}\s*[A-Z]?$"
    words_before_price = re.split(price_pattern, text)

    if not words_before_price:
        return text

    last_word = words_before_price[-1]

    # Словари диакритики по локалям
    diacritics_maps = {
        "de_DE": {"rose": "rosé", "rose": "Rosé"},
        "pl_PL": {"szynka": "sztynka"},
        "cs_CZ": {"sterka": "stěrka"},
        # ... другие карты
    }

    # Поиск в словаре
    locale_map = diacritics_maps.get(locale, {})
    for base, with_diacritics in locale_map.items():
        if base in last_word:
            return last_word.replace(base, with_diacritics)

    return text
```

**Пример:**
```python
# Было: Prosecco rose 6,99 B
# Стало: Prosecco rosé 6,99 B
```

---

### 4. Garbage Filtering (GARBAGE)

**Ответственный модуль:** `garbage_filter.py`

#### Правило 8: Удаление маскированного мусора

**ID:** `remove_masked_garbage`

**Тип:** `GARBAGE`

**Паттерн:** `H***@`, `H****9`, `****`, `***`

**Замена:** Удалить или заменить на пробел

**Уверенность:** 0.95

**Логика:**
```python
def remove_masked_garbage(text: str) -> str:
    # Паттерны маскированного текста
    patterns = [
        r"\*{2,}[@]\*",      # H***@
        r"\*{4}",             # ****
        r"\*{3,}",            # ***
    ]

    result = text
    for pattern in patterns:
        result = re.sub(pattern, " ", result)

    return result.strip()
```

**Пример:**
```python
# Было: H***@ 450
# Стало: (пробел) 450
```

---

## Конфигурация правил

### Формат YAML-файла

```yaml
# src/parsing/locales/cleanup_rules.yaml

version: 1.0

# Универсальные правила (для всех локалей)
universal:
  char_replacements:
    - id: "masked_garbage"
      pattern: "\\*{3,}"
      replacement: " "
      confidence: 0.95

# Locale-specific правила
locales:
  de_DE:
    char_replacements:
      - id: "header_press"
        pattern: "^rebe$"
        replacement: "PRESS"
        context: "header"
        confidence: 0.90

      - id: "oliven_ole"
        pattern: "Olivenole"
        replacement: "Olivenöl"
        confidence: 0.95

    missing_char_restoration:
      - id: "schweinenacken"
        pattern: "Schweinenacken"
        replacement: "Schweinenacken"
        confidence: 0.85

    diacritics_restoration:
      - id: "prosecco_rose"
        pattern: "rose"
        replacement: "rosé"
        context: "before_price"
        confidence: 0.90

  pl_PL:
    diacritics_restoration:
      - id: "szynka"
        pattern: "szynka"
        replacement: "sztynka"
        confidence: 0.95

  th_TH:
    # Пока нет данных, оставляем пустым
```

---

## Порядок применения правил

### Важно: Правила должны применяться в ПРАВИЛЬНОМ порядке

```
1. Garbage Removal         # Сначала убрать мусор
2. Unicode Normalization    # Нормализировать Unicode
3. Word Merging/Splitting # Исправить структуру слов
4. Character Replacement   # Заменить символы
5. Diacritics Restoration # Восстановить диакритику
```

### Пример работы конвейера

```python
from .garbage_filter import remove_masked_garbage
from .unicode_normalizer import normalize_unicode
from .word_merger import split_merged_words
from .char_replacer import replace_characters
from .diacritics_restorer import restore_diacritics

def cleanup_text(text: str, locale: str) -> str:
    # 1. Remove garbage
    text = remove_masked_garbage(text)

    # 2. Normalize Unicode
    text = normalize_unicode(text)

    # 3. Fix word structure
    text = split_merged_words(text)

    # 4. Replace characters
    text = replace_characters(text, locale)

    # 5. Restore diacritics
    text = restore_diacritics(text, locale)

    return text
```

---

## Метрики качества

### Измерение эффективности

Для каждого правила нужно измерять:

| Метрика | Описание | Цель |
|---------|-----------|--------|
| Precision | Как часто правило правильно применилось | > 95% |
| Recall | Как часто правило сработало на реальных ошибках | > 90% |
| F1-score | Гармоническое среднее | > 0.92 |
| False Positive Rate | Сколько правильных слов испорчено | < 1% |

### Тестирование

Для каждого правила нужны:

1. **Positive тесты:** Правило должно исправить ошибку
2. **Negative тесты:** Правило не должно испортить правильный текст
3. **Regression тесты:** Проверка на существующем наборе чеков

---

## Рекомендуемый план реализации

### Фаза 1: Базовые правила (1 неделя)

- [x] Создать модульную структуру
- [ ] Реализовать `garbage_filter.py`
- [ ] Реализовать `unicode_normalizer.py`
- [ ] Реализовать `word_merger.py`
- [ ] Реализовать `rules_loader.py` (YAML)
- [ ] Написать базовые тесты

### Фаза 2: Character Replacement (1 неделя)

- [ ] Реализовать `char_replacer.py`
- [ ] Добавить словари для de_DE
- [ ] Добавить правила для CHAR_SUB
- [ ] Добавить правила для CHAR_MISS
- [ ] Написать тесты

### Фаза 3: Diacritics (3 дня)

- [ ] Реализовать `diacritics_restorer.py`
- [ ] Добавить карты диакритики для всех локалей
- [ ] Написать тесты

### Фаза 4: Интеграция (2 дня)

- [ ] Объединить все модули в `stage.py`
- [ ] Создать YAML конфигурацию
- [ ] Интегрировать в pipeline
- [ ] Тестирование на всех локалей

### Фаза 5: Оптимизация (3 дня)

- [ ] Сбор метрик качества
- [ ] A/B тестирование правил
- [ ] Добавить новые правила по мере анализа
- [ ] Документация

---

## Следующие шаги

### Для продолжения анализа

1. Проанализировать ещё 9+ немецких чеков
2. Добавить новые правила в cleanup_rules.yaml
3. Проанализировать польские чеки (диакритика)
4. Проанализировать тайские чеки (нелатинский скрипт)

### Для реализации s1_ocr_cleanup

1. Создать модули по архитектуре выше
2. Реализовать правила из этого документа
3. Написать тесты (unit + integration)
4. Интегрировать в pipeline

---

## Связанные документы

- [ARTIFACT_TYPES.md](ARTIFACT_TYPES.md) - классификатор артефактов
- [MATRIX.md](MATRIX.md) - агрегированная матрица
- [by_locale/](by_locale/) - детальные артефакты
- [README.md](README.md) - методология анализа
