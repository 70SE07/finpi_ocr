# План реорганизации проекта Finpi OCR

## Статус
**В работе** (31.12.2024)

### Прогресс
- [x] Фаза 1.1: Контракты на Pydantic
- [x] Фаза 1.2: Интеграция контрактов в код
- [x] Фаза 2.1: Структура stages/
- [x] Фаза 2.2: Реализация этапов и пайплайна
- [x] Фаза 2.3: Синхронизация документации
- [x] Фаза 3.1: Интеграция нового пайплайна со скриптами
- [ ] Фаза 3.2: Сравнительное тестирование
- [ ] Фаза 3.3: Интеграционные тесты на Ground Truth
- [ ] Фаза 4.1: README безопасность
- [ ] Фаза 4.2: Аудит конфигурации

## Цель

Привести кодовую базу в соответствие с утверждённой системной архитектурой (ADR-001 — ADR-015).

---

## Фаза 1: Контракты и валидация

### 1.1 Контракты на Pydantic

**Проблема:** `contracts/d1_extraction_dto.py` использует `dataclass`, не Pydantic. Нет валидации.

**Решение:**
```python
# contracts/d1_extraction_dto.py
from pydantic import BaseModel, Field, field_validator

class BoundingBox(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)

class Word(BaseModel):
    text: str = Field(..., min_length=1)
    bounding_box: BoundingBox
    confidence: float = Field(1.0, ge=0.0, le=1.0)

class RawOCRResult(BaseModel):
    full_text: str = ""
    words: list[Word] = Field(default_factory=list)
    metadata: OCRMetadata | None = None
    
    model_config = ConfigDict(frozen=True)
```

**Файлы:**
- [x] `contracts/d1_extraction_dto.py` — переписан на Pydantic ✅
- [x] `contracts/d2_parsing_dto.py` — проверен, Pydantic v2 ✅
- [x] `contracts/d3_categorization_dto.py` — обновлён на Pydantic v2 ✅
- [x] `contracts/README.md` — документация контрактов ✅

---

### 1.2 Интеграция контрактов в код

**Проблема:** `src/` не использует контракты из `contracts/`.

**Решение:**
- D1 (`src/extraction/`) должен возвращать `RawOCRResult` из `contracts/`
- D2 (`src/parsing/`) должен принимать `RawOCRResult` и возвращать `RawReceiptDTO`

**Файлы:**
- [x] `contracts/raw_ocr_schema.py` — УДАЛЁН (устаревший dataclass) ✅
- [x] `contracts/__init__.py` — обновлён, экспорт всех DTO ✅
- [x] `src/extraction/ocr/google_vision_ocr.py` — возвращает `RawOCRResult` из `contracts/` ✅
- [x] `src/extraction/domain/interfaces.py` — типы из `contracts/` ✅
- [x] `src/extraction/application/extraction_pipeline.py` — использует `RawOCRResult` ✅
- [x] `src/extraction/infrastructure/adapters/google_vision_adapter.py` — обновлён ✅
- [x] `scripts/extract_raw_ocr.py` — использует `contracts.d1_extraction_dto` ✅
- [x] `scripts/parse_receipt.py` — использует `contracts.d1_extraction_dto` ✅

---

## Фаза 2: Пайплайн D2 по ADR-015

### 2.1 Структура пайплайна

**Проблема:** Текущий пайплайн не соответствует утверждённым 6 этапам.

**Решение:** Реструктуризация `src/parsing/`:

```
src/parsing/
├── stages/                    # 6 этапов пайплайна
│   ├── __init__.py
│   ├── 1_layout_processor.py      # Layout Processing
│   ├── 2_locale_detector.py       # Locale Detection
│   ├── 3_store_detector.py        # Store Detection
│   ├── 4_metadata_extractor.py    # Metadata Extraction
│   ├── 5_semantic_extractor.py    # Semantic Extraction (Items)
│   └── 6_validator.py             # Validation (Checksum)
├── application/
│   └── parsing_pipeline.py        # Оркестратор этапов
├── locales/                   # Конфиги локалей
│   ├── de_DE/
│   │   ├── config.yaml
│   │   └── stores/            # Store configs (исключения)
│   │       └── lidl.yaml
│   └── pl_PL/
│       └── config.yaml
└── domain/
    ├── interfaces.py          # Интерфейсы этапов
    └── exceptions.py
```

**Файлы:**
- [x] `src/parsing/stages/__init__.py` — экспорт всех этапов ✅
- [x] `src/parsing/stages/stage_1_layout.py` — Layout Processing ✅
- [x] `src/parsing/stages/stage_2_locale.py` — Locale Detection ✅
- [x] `src/parsing/stages/stage_3_store.py` — Store Detection ✅
- [x] `src/parsing/stages/stage_4_metadata.py` — Metadata Extraction ✅
- [x] `src/parsing/stages/stage_5_semantic.py` — Semantic Extraction ✅
- [x] `src/parsing/stages/stage_6_validation.py` — Validation (Checksum) ✅
- [x] `src/parsing/stages/pipeline.py` — ParsingPipeline (оркестратор) ✅

---

### 2.2 Каждый этап — SRP

По ADR-013 (Clean Code, SRP) каждый этап имеет:
- Свой ЦКП
- Единственную ответственность
- Интерфейс (для тестирования)

```python
# src/parsing/domain/interfaces.py
from abc import ABC, abstractmethod

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

## Фаза 3: Интеграция и тестирование

### 3.1 Интеграция со скриптами

**Статус:** ЗАВЕРШЕНО

**Решение:** Прямое обновление (без адаптера — over-engineering для R&D стенда).

**Созданные скрипты:**
- [x] `scripts/run_d2_pipeline.py` — тестовый запуск нового ParsingPipeline ✅
- [x] `scripts/compare_pipelines.py` — сравнение OLD (ReceiptParser) vs NEW (ParsingPipeline) ✅

**Обновлённые компоненты:**
- [x] `src/extraction/application/factory.py` — обновлена под новый интерфейс ExtractionPipeline ✅

**Первый тест (IMG_1292.jpeg):**
```
D1: 358 слов, 7 сек
D2: 78 строк -> de_DE -> 35 товаров -> CHECKSUM FAILED (diff: 602.62)
```
Checksum fail ожидаем — этапы требуют доработки (неправильно извлечена итоговая сумма).

---

### 3.2 Checksum валидация

**Статус:** ЗАВЕРШЕНО (Stage 6 реализован)

**Решение:** Этап 6 (Validator) в пайплайне:

```python
# src/parsing/stages/6_validator.py
class ChecksumValidator:
    TOLERANCE = 0.05  # ADR-011
    
    def validate(self, items: list[Item], receipt_total: float) -> ValidationResult:
        items_sum = sum(item.total for item in items)
        difference = abs(items_sum - receipt_total)
        
        if difference <= self.TOLERANCE:
            return ValidationResult(passed=True, difference=difference)
        else:
            # По ADR-009: это баг системы, не проблема чека
            raise ChecksumMismatchError(
                f"Checksum failed: items_sum={items_sum}, receipt_total={receipt_total}, diff={difference}"
            )
```

---

### 3.3 Сравнительное тестирование

**Статус:** В ПРОЦЕССЕ

**Цель:** Убедиться что новый ParsingPipeline работает не хуже старого ReceiptParser.

#### Отладка Stage 4 и Stage 5 (2026-01-01)

**Проблемы и исправления (системные):**

| Проблема | Stage | Решение |
|----------|-------|---------|
| Итоговая сумма 12.31 вместо 143.37 | Stage 4 | Добавлен `betrag` в TOTAL_KEYWORDS; улучшена логика выбора (приоритет нижней части, наибольшая сумма) |
| Строки веса парсятся как товары | Stage 5 | Добавлен паттерн `WEIGHT_LINE_PATTERNS` для `X,XXX kg x Y,YY EUR/kg` |
| Строки итогов парсятся как товары | Stage 5 | Добавлены `zu zahlen`, `karte`, `kartenzahlung` в SKIP_KEYWORDS |
| Налоговые строки парсятся как товары | Stage 5 | Добавлен паттерн `TAX_LINE_PATTERNS` для `A 7 %`, `B 19 %` |
| qty=29 вместо qty=2 (из цены 4,29) | Stage 5 | Исправлен regex для quantity: `(?:^|\s)(\d{1,3})\s*[xX×]\s*(?:\d|$)` |

**Результаты тестирования:**

| Чек | Локаль | Результат | Комментарий |
|-----|--------|-----------|-------------|
| IMG_1292 | de_DE | **PASSED** | Checksum: 143.37 = 143.37 |
| IMG_1336 | de_DE | **PASSED** | Checksum: 146.32 = 146.32 |
| IMG_1352 | de_DE | FAILED (diff: 37.02) | Требует отладки |
| PL_001 | pl_PL | FAILED (diff: 98.57) | Требует отладки |
| PT_001 | pt_PT | FAILED (diff: 0.99) | Требует отладки |

**Скрипт:** `scripts/compare_pipelines.py`

```bash
# Один чек
python3 scripts/compare_pipelines.py data/input/IMG_1292.jpeg

# Все чеки
python3 scripts/compare_pipelines.py --all

# Первые 5 чеков
python3 scripts/compare_pipelines.py --all --limit 5
```

**Метрики сравнения:**
- locale_match — совпадает ли определённая локаль
- total_match — совпадает ли итоговая сумма (±0.01)
- items_match — совпадает ли количество товаров
- time_ratio — отношение времени NEW/OLD

---

### 3.4 Интеграционные тесты на Ground Truth

**Статус:** ПЛАНИРУЕТСЯ

**Проблема:** Нет автоматизированных тестов на эталонных чеках.

**Решение:**

```python
# tests/integration/test_ground_truth.py
import pytest
from pathlib import Path

GROUND_TRUTH_DIR = Path("docs/ground_truth")

@pytest.fixture
def ground_truth_files():
    return list(GROUND_TRUTH_DIR.glob("*.json"))

def test_all_ground_truth_pass_checksum(ground_truth_files):
    """Все Ground Truth файлы должны проходить checksum."""
    for gt_file in ground_truth_files:
        gt = load_ground_truth(gt_file)
        items_sum = sum(item["total_price"] for item in gt["items"])
        receipt_total = gt["metadata"]["receipt_total"]
        
        assert abs(items_sum - receipt_total) <= 0.05, f"Checksum failed for {gt_file.name}"
```

**Файлы:**
- [ ] `tests/integration/test_ground_truth.py`
- [ ] `tests/integration/test_pipeline_de_DE.py`
- [ ] `tests/integration/test_pipeline_pl_PL.py`

---

## Фаза 4: Безопасность и конфигурация

### 4.1 README предупреждение

**Файл:** `README.md`

```markdown
## Безопасность

⚠️ **ВАЖНО:** Файл `config/google_credentials.json` содержит секретные ключи.

- НИКОГДА не коммитьте этот файл в Git
- Файл уже добавлен в `.gitignore`
- Используйте переменную окружения `GOOGLE_APPLICATION_CREDENTIALS`
```

---

### 4.2 Централизованная конфигурация

**Проблема:** Некоторые настройки могут быть захардкожены в коде.

**Решение:** Аудит и вынос в `config/settings.py`:
- [ ] Проверить все файлы на магические числа
- [ ] Вынести в `settings.py` с комментариями

---

## Порядок выполнения

| Фаза | Задача | Приоритет | Статус |
|------|--------|-----------|--------|
| 1.1 | Контракты на Pydantic | 🔴 Критично | DONE |
| 1.2 | Интеграция контрактов | 🔴 Критично | DONE |
| 2.1 | Структура stages/ | 🔴 Критично | DONE |
| 2.2 | Реализация этапов | 🔴 Критично | DONE |
| 2.3 | Синхронизация документации | 🔴 Критично | DONE |
| 3.1 | Интеграция со скриптами | 🔴 Критично | DONE |
| 3.2 | Checksum валидация (Stage 6) | 🔴 Критично | DONE |
| 3.3 | Сравнительное тестирование | 🟡 Важно | IN PROGRESS |
| 3.4 | Интеграционные тесты | 🟡 Важно | TODO |
| 4.1 | README безопасность | 🟢 Минорно | TODO |
| 4.2 | Аудит конфигурации | 🟢 Минорно | TODO |

---

## Критерий завершения

Реорганизация завершена когда:
1. ✅ Контракты на Pydantic с валидацией
2. ✅ D1 возвращает `RawOCRResult`, D2 возвращает `RawReceiptDTO`
3. ✅ Пайплайн D2 = 6 этапов (Layout→Locale→Store→Metadata→Items→Validation)
4. ✅ Checksum валидация в основном коде
5. ✅ Интеграционные тесты на Ground Truth проходят
6. ✅ README с предупреждением о безопасности

---

## Связанные документы

- [PROJECT_VISION.md](PROJECT_VISION.md) — фундаментальные принципы
- [ADR-015: Этапы пайплайна D2](architecture/decisions/015_d2_pipeline_stages.md)
- [ADR-013: Clean Code и SRP](architecture/decisions/013_clean_code_srp.md)
- [ADR-011: Стратегия валидации](architecture/decisions/011_validation_strategy.md)
