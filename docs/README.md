# Документация проекта Finpi OCR

Добро пожаловать в структурированный архив знаний проекта. Здесь поддерживается идеальный порядок для обеспечения SRP и прозрачности архитектуры.

## Структура директории

### [/architecture](file:///Users/sergejevsukov/Downloads/Finpi_OCR/docs/architecture)
Фундаментальные решения, схемы и правила взаимодействия модулей.
- [contract_registry.md](file:///Users/sergejevsukov/Downloads/Finpi_OCR/docs/architecture/contract_registry.md) — Главный реестр обязательств (ЦКП) каждого модуля.

### [/hypotheses](file:///Users/sergejevsukov/Downloads/Finpi_OCR/docs/hypotheses)
Результаты экспериментов, Blue Channel тесты и A/B отчеты.

---

## Правила работы с документацией
1. **Актуальность:** При изменении ЦКП модуля, в первую очередь обновляется `contract_registry.md`.
2. **Интуитивность:** Документ должен быть понятен без глубокого погружения в код.
3. **Системность:** Документируем алгоритмические решения, а не разовые фиксы.
