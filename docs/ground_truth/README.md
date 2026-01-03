# Ground Truth - Эталонные данные чеков

## Определение

**Ground Truth = Эталон** - то, что РЕАЛЬНО написано на бумажном чеке.

**Как создается:** Визуальный анализ изображения чека (не результат OCR).

**Источник истины:** Человек (или AI) смотрит на изображение и записывает что там написано.

---

## Структура папок

```
docs/ground_truth/
├── bg_BG/          # Болгария
├── cs_CZ/          # Чехия
├── de_DE/          # Германия (42 файла)
├── en_IN/          # Индия
├── es_ES/          # Испания
├── pl_PL/          # Польша
├── pt_PT/          # Португалия
├── th_TH/          # Таиланд (16 файлов)
├── tr_TR/          # Турция
├── uk_UA/          # Украина
├── README.md       # Этот файл
└── template.json   # Шаблон для новых файлов
```

**Правило нумерации:** ID = порядковый номер ВНУТРИ папки локали (001, 002, 003...)

---

## Назначение

Ground Truth используется для проверки качества **всего пайплайна**:

| Домен | Что проверяем | Вопрос |
|-------|---------------|--------|
| **D1 (OCR)** | RAW OCR текст | Все ли прочитали? Ничего не потеряно? |
| **D2 (Parsing)** | Структурированные данные | Не потеряли ли при структуризации? |

---

## Статистика

| Метрика | Значение |
|---------|----------|
| **Всего файлов** | **79** |
| **Локалей** | **10** |

### По локалям

| Локаль | Файлов | Магазины |
|--------|--------|----------|
| de_DE | 42 | Lidl, ALDI, dm, EDEKA, HIT, Penny, Shell, Netto... |
| th_TH | 16 | 7-Eleven, CP, Big C, McDonald's, Gloria Jean's... |
| pl_PL | 9 | Carrefour, Cropp, Orlen, Leroy Merlin, Zabka |
| es_ES | 3 | Consum, Mercadona |
| pt_PT | 3 | Continente, Lidl |
| tr_TR | 2 | F33 ENVA, BTA |
| bg_BG | 1 | Billa |
| cs_CZ | 1 | Hornbach |
| en_IN | 1 | NYBC |
| uk_UA | 1 | Dnipro-M |

---

## Формат файлов

### Имя файла
```
{ID}_{locale}_{store}_{image_name}.json
```

Примеры:
- `001_de_DE_lidl_IMG_1292.json`
- `008_de_DE_aldi_IMG_1724.json`
- `001_th_TH_7eleven_IMG_2461.json`

### Структура JSON

```json
{
  "id": "001",
  "source_file": "data/input/IMG_1292.jpeg",
  "locale": "de_DE",
  "store": {
    "name": "Lidl",
    "address": "адрес магазина"
  },
  "metadata": {
    "date": "31.07.2025",
    "time": "12:41",
    "currency": "EUR",
    "payment_method": "Kartenzahlung",
    "receipt_total": 143.37
  },
  "items": [
    {"raw_name": "Schweinenackenbraten", "quantity": 1.207, "unit": "kg", "unit_price": 8.99, "total_price": 10.85},
    {"raw_name": "Preisvorteil", "total_price": -0.30, "is_discount": true}
  ],
  "validation": {
    "checksum_method": "SUM(items) == receipt_total",
    "expected_total": 143.37,
    "discrepancy": 0.00
  }
}
```

---

## Использование

```python
import json
from pathlib import Path

def load_ground_truth(locale: str, receipt_id: str) -> dict:
    """Загрузить эталонные данные чека."""
    gt_dir = Path("docs/ground_truth") / locale
    for file in gt_dir.glob(f"{receipt_id}_*.json"):
        with open(file) as f:
            return json.load(f)
    raise FileNotFoundError(f"Ground truth {receipt_id} not found in {locale}")

# Пример
gt = load_ground_truth("de_DE", "001")
print(f"Total: {gt['metadata']['receipt_total']} {gt['metadata']['currency']}")
```

---

## Создание нового Ground Truth

См. документ: [AI_GROUND_TRUTH_ALGORITHM.md](../AI_GROUND_TRUTH_ALGORITHM.md)

**Краткий алгоритм:**
1. Получить изображение чека
2. Определить локаль (de_DE, th_TH, etc.)
3. Посмотреть последний ID в папке локали
4. Создать файл `{next_id}_{locale}_{store}_{image}.json`
5. Проверить checksum: `sum(items) == receipt_total`

---

## Проверка консистентности

```bash
cd /path/to/Finpi_OCR
python3 scripts/check_gt_consistency.py
```

Ожидаемый результат:
```
=== Статистика Ground Truth ===
Всего файлов: 79
OK: 79
С проблемами: 0
```

---

## Важные особенности

1. **ID = номер в имени файла** (не глобальный, а внутри локали)
2. **raw_name = точная копия** с чека (не исправлять!)
3. **Скидки = отрицательные позиции** с `is_discount: true`
4. **Checksum обязателен** — sum(items) должен равняться receipt_total
