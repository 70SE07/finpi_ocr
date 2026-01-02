# Документация проекта Finpi OCR

Структурированный архив знаний проекта. SRP и прозрачность архитектуры.

---

## НАЧНИ ОТСЮДА

### [PROJECT_VISION.md](./PROJECT_VISION.md) — Видение проекта

**Обязательно к прочтению.** Философия проекта:
- Почему 100% качество — требование, не цель
- Почему 0% расхождений — единственный допустимый результат
- Принцип Stage = SRP = ЦКП
- Системные решения vs костыли

### [GLOSSARY.md](./GLOSSARY.md) — Глоссарий

Справочник терминов. Единый язык проекта:
- Домен, Pipeline, Phase, Stage, Operation
- ЦКП, SRP, Контракт, Ground Truth

---

## Планы реорганизации

### [REORGANIZATION_D2.md](./REORGANIZATION_D2.md) — Домен 2 (Parsing)

**Текущая работа.** Приведение D2 в соответствие с ADR-015:
- Пайплайн = 6 этапов (Layout→Locale→Store→Metadata→Items→Validation)
- Checksum валидация
- Интеграционные тесты на Ground Truth

---

## Структура директории

### [/architecture](./architecture/)

Фундаментальные решения и правила:
- [architecture_overview.md](./architecture/architecture_overview.md) — обзор архитектуры, домены, контракты
- [contract_registry.md](./architecture/contract_registry.md) — реестр ЦКП модулей
- [/decisions/](./architecture/decisions/) — ADR (Architecture Decision Records)

### [/ground_truth](./ground_truth/)

Эталонные данные чеков. **Неприкосновенны.**
- 77 JSON файлов с проверенными данными
- [RECEIPT_GROUND_TRUTH_PROTOCOL.md](./RECEIPT_GROUND_TRUTH_PROTOCOL.md) — протокол создания

### [/patterns](./patterns/)

Паттерны чеков для построения D2:
- [README.md](./patterns/README.md) — стандарт документирования
- [MATRIX.md](./patterns/MATRIX.md) — агрегированная матрица паттернов
- [/by_store/](./patterns/by_store/) — паттерны по магазинам

### [/locales](./locales/)

Анализ локалей (de_DE, pl_PL, pt_PT, th_TH, etc.)

### [/research](./research/)

Исследования и эксперименты:
- Исследования DTO и контрактов
- Гипотезы и A/B тесты

---

## Правила работы с документацией

1. **Один источник правды:**
   - Философия → `PROJECT_VISION.md`
   - Термины → `GLOSSARY.md`
   - Контракты → `contract_registry.md`

2. **Актуальность:** При изменении архитектуры обновляем документацию.

3. **Системность:** Документируем паттерны, не разовые фиксы.
