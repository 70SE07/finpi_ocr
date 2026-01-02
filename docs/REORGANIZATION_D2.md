# План реорганизации Домена 2 (Parsing)

**Статус:** ЗАВЕРШЕНО (2026-01-02)

---

## Цель

Привести D2 (Parsing) в соответствие с утверждённой архитектурой (ADR-015) и обеспечить 100% качество обработки чеков согласно PROJECT_VISION.

---

## Прогресс

- [x] Фаза 1: Структура stages/
- [x] Фаза 2: Реализация этапов и пайплайна
- [x] Фаза 3: Интеграция со скриптами
- [x] Фаза 4: Checksum валидация (Stage 6)
- [x] Фаза 5: Сравнительное тестирование
- [x] Фаза 6: Аварийный анализ и исправление системы
- [x] Фаза 7: Расширение тестирования по видению

---

## Фаза 1: Структура пайплайна

**Статус:** ЗАВЕРШЕНО

**Решение:** Реструктуризация `src/parsing/` по ADR-015:

```
src/parsing/
├── stages/                    # 6 этапов пайплайна
│   ├── __init__.py
│   ├── stage_1_layout.py      # Layout Processing
│   ├── stage_2_locale.py      # Locale Detection
│   ├── stage_3_store.py       # Store Detection
│   ├── stage_4_metadata.py    # Metadata Extraction
│   ├── stage_5_semantic.py    # Semantic Extraction (Items)
│   ├── stage_6_validation.py  # Validation (Checksum)
│   └── pipeline.py            # ParsingPipeline (оркестратор)
├── locales/                   # Конфиги локалей
└── domain/
    ├── interfaces.py          # Интерфейсы этапов
    └── exceptions.py
```

---

## Фаза 2: Каждый этап — SRP

**Статус:** ЗАВЕРШЕНО

По ADR-013 (Clean Code, SRP) каждый этап имеет:
- Свой ЦКП
- Единственную ответственность
- Интерфейс (для тестирования)

```python
# src/parsing/domain/interfaces.py
class ILayoutProcessor(ABC):
    @abstractmethod
    def process(self, raw_ocr: RawOCRResult) -> LayoutResult: ...

class ILocaleDetector(ABC):
    @abstractmethod
    def detect(self, layout: LayoutResult) -> str: ...

class IStoreDetector(ABC):
    @abstractmethod
    def detect(self, layout: LayoutResult, locale_config: LocaleConfig) -> StoreResult | None: ...

# ... и так далее для всех 6 этапов
```

---

## Фаза 3: Интеграция со скриптами

**Статус:** ЗАВЕРШЕНО

**Созданные скрипты:**
- [x] `scripts/run_d2_pipeline.py` — тестовый запуск ParsingPipeline
- [x] `scripts/compare_pipelines.py` — сравнение OLD vs NEW

---

## Фаза 4: Checksum валидация

**Статус:** ЗАВЕРШЕНО

Stage 6 (Validator) в пайплайне:

```python
class ChecksumValidator:
    TOLERANCE = 0.05  # ADR-011
    
    def validate(self, items: list[Item], receipt_total: float) -> ValidationResult:
        items_sum = sum(item.total for item in items)
        difference = abs(items_sum - receipt_total)
        
        if difference <= self.TOLERANCE:
            return ValidationResult(passed=True, difference=difference)
        else:
            raise ChecksumMismatchError(...)
```

---

## Фаза 5: Сравнительное тестирование

**Статус:** ЗАВЕРШЕНО

### Исправления (системные)

| Проблема | Stage | Решение |
|----------|-------|---------|
| Итоговая сумма неверная | Stage 4 | Добавлен `betrag` в TOTAL_KEYWORDS |
| Строки веса как товары | Stage 5 | Паттерн `WEIGHT_LINE_PATTERNS` |
| Строки итогов как товары | Stage 5 | SKIP_KEYWORDS расширен |
| Налоговые строки как товары | Stage 5 | Паттерн `TAX_LINE_PATTERNS` |
| qty из цены (4,29 → qty=29) | Stage 5 | Исправлен regex quantity |

### Результаты

| Чек | Локаль | Результат |
|-----|--------|-----------|
| IMG_1292 | de_DE | **PASSED** |
| IMG_1336 | de_DE | **PASSED** |
| IMG_1352 | de_DE | **PASSED** (Ground Truth создан) |
| PL_001 | pl_PL | **PASSED** |
| PT_001 | pt_PT | **PASSED** |

---

## Фаза 6: Аварийный анализ

**Статус:** ЗАВЕРШЕНО

**Принцип:** Ground Truth неприкосновенен. Все FAILED — баги системы.

### RCA и исправления

| Чек | Проблема | RCA | Исправление |
|-----|----------|-----|-------------|
| IMG_1352 | Отсутствовал GT | GT не существовал | Создан `079_de_DE_tankstelle_IMG_1352.json` |
| PL_001 | +10.28 PLN | Multi-price split неправильно обрабатывал весовые товары | Stage 5: Добавлен паттерн весовых товаров `qty price total` без `*` |
| PT_001 | +1.49 EUR | Price Sanity Check фильтровал легитимный товар | Stage 5: Порог не применяется для чеков < 20 EUR |

### Системные исправления (Stage 5)

1. **Паттерн весовых товаров без маркера:**
   - Формат: `NAME qty price total TAX` (польский Carrefour)
   - Пример: `C_CYTRYNY LUZ 0,29 9,99 2,90 C`
   - Проверка: `qty < 10 && qty * price ≈ total`

2. **Адаптивный порог Price Sanity Check:**
   - Чеки < 20 EUR/PLN: порог отключен
   - Чеки 20-50: порог 50%
   - Чеки > 50: порог 40% (короткие) / 25% (длинные)

---

## Фаза 7: Расширение тестирования

**Статус:** ЗАВЕРШЕНО

Создан `tests/integration/test_d2_ground_truth.py`:

| Тест | Метрика | Описание |
|------|---------|----------|
| `test_checksum_validation` | Checksum | SUM(items) == receipt_total |
| `test_items_count` | Количество товаров | Погрешность ±2 |
| `test_total_amount` | Итоговая сумма | Точное совпадение ±0.05 |

Запуск: `pytest tests/integration/test_d2_ground_truth.py -v`

---

## Очистка Legacy кода

**Статус:** ЗАВЕРШЕНО

### Удалённые компоненты

| Компонент | Причина удаления |
|-----------|------------------|
| `src/parsing/parser/` | OLD парсер, заменён на `stages/pipeline.py` |
| `src/parsing/application/` | Мёртвый код (Clean Arch wrapper) |
| `src/parsing/infrastructure/adapters/` | Адаптеры для OLD парсера |
| `src/parsing/dto/` | OLD DTO (`OcrResultDTO`) |
| `src/parsing/old_project/` | Legacy код |
| `scripts/parse_receipt.py` | Использовал OLD парсер |
| `scripts/compare_pipelines.py` | Сравнение OLD vs NEW |

### Обновлённые компоненты

| Компонент | Изменение |
|-----------|-----------|
| `scripts/run_pipeline.py` | Использует `run_d2_pipeline.py` |
| `src/parsing/__init__.py` | Экспортирует `ParsingPipeline`, `ConfigLoader` |

### Итоговая структура D2

```
src/parsing/
├── stages/                    # 6 этапов пайплайна (PRIMARY)
│   ├── stage_1_layout.py
│   ├── stage_2_locale.py
│   ├── stage_3_store.py
│   ├── stage_4_metadata.py
│   ├── stage_5_semantic.py
│   ├── stage_6_validation.py
│   └── pipeline.py            # ParsingPipeline
├── locales/                   # Конфиги локалей (YAML)
│   ├── config_loader.py
│   ├── de_DE/
│   ├── pl_PL/
│   └── ...
├── domain/                    # Интерфейсы
└── __init__.py                # Публичный API
```

---

## Критерий завершения

D2 реорганизация завершена когда:

1. ✅ **0 FAILED тестов** — все указанные FAILED чеки исправлены
2. ✅ **Все метрики видения** проверяются автоматически
3. ✅ **Ground Truth неприкосновенен**
4. ✅ **Системные решения** задокументированы
5. ✅ **Пайплайн D2** = 6 этапов (Layout→Locale→Store→Metadata→Items→Validation)
6. ✅ **Legacy код удалён** — только `stages/` в D2

---

## Фаза 8: Рефакторинг Stage 3 (Store Detection)

**Статус:** ЗАВЕРШЕНО (2026-01-02)

### Проблема

Stage 3 содержал хардкод магазинов в `KNOWN_STORES` dict:
- При 100 локалях = 2000+ строк хардкода в Python
- Нарушение принципа "системных решений на уровне проекта"
- Невозможность добавить магазин без изменения Python кода

### Решение

**Системный принцип:** 0 хардкода магазинов в Python.

1. Создан `StoreDetectionConfig` dataclass в `config_loader.py`
2. Расширен `LocaleConfig` полем `stores: List[StoreDetectionConfig]`
3. Добавлен метод `_scan_stores_for_detection()` в ConfigLoader
4. Каждый магазин имеет свой YAML файл с секцией `detection`:

```yaml
# stores/lidl.yaml
detection:
  brands:
    - lidl
    - lidl plus
  aliases:
    - LIDL STIFTUNG
  priority: 1
```

### Результат

| Метрика | До | После |
|---------|-----|-------|
| Строки хардкода магазинов | ~50 | 0 |
| Добавление нового магазина | Изменение Python | Создание YAML |
| Магазинов de_DE | 19 | 19 (в YAML) |
| Магазинов pl_PL | 15 | 15 (в YAML) |
| Магазинов es_ES | 10 | 10 (в YAML) |
| Магазинов pt_PT | 8 | 8 (в YAML) |
| Магазинов cs_CZ | 9 | 9 (в YAML) |

### Структура stores/

```
locales/
├── de_DE/
│   ├── parsing.yaml
│   └── stores/
│       ├── aldi.yaml
│       ├── lidl.yaml
│       ├── rewe.yaml
│       ├── edeka.yaml
│       └── ... (15+ магазинов)
├── pl_PL/
│   └── stores/
│       ├── biedronka.yaml
│       ├── lidl.yaml
│       └── ... (10+ магазинов)
└── ...
```

### Тесты

- `tests/unit/parsing/test_config_loader_stores.py` — загрузка магазинов из YAML
- `tests/unit/parsing/test_stage_3_store.py` — детекция магазинов

---

## Связанные документы

- [PROJECT_VISION.md](PROJECT_VISION.md) — философия 100% качества
- [ADR-015](architecture/decisions/015_d2_pipeline_stages.md) — этапы пайплайна D2
- [ADR-013](architecture/decisions/013_clean_code_srp.md) — Clean Code и SRP
- [ADR-011](architecture/decisions/011_validation_strategy.md) — стратегия валидации
- [ADR-009](architecture/decisions/009_d2_quality_guarantees.md) — гарантии качества D2
