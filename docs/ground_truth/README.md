# Ground Truth - Эталонные данные чеков

## Определение

**Ground Truth = Эталон** - то, что РЕАЛЬНО написано на бумажном чеке.

**Как создается:** Визуальный анализ изображения чека (не результат OCR).

**Источник истины:** Человек (или AI) смотрит на изображение и записывает что там написано.

---

## Назначение

Ground Truth используется для проверки качества **всего пайплайна**:

| Домен | Что проверяем | Вопрос |
|-------|---------------|--------|
| **D1 (OCR)** | RAW OCR текст | Все ли прочитали? Ничего не потеряно? |
| **D2 (Parsing)** | Структурированные данные | Не потеряли ли при структуризации? Корректно ли разложили? |

### Проверка D1 (Extraction)
- Сравниваем RAW OCR текст с тем, что реально на чеке
- Проверяем: OCR ничего не пропустил? Все слова распознаны?

### Проверка D2 (Parsing)
- Сравниваем структурированный output (items, metadata) с Ground Truth
- Проверяем: Парсинг ничего не потерял? Данные корректно разложены?

---

## Содержимое папки

Папка содержит **эталонные JSON-файлы** для каждого проанализированного чека.

## Формат файлов

Каждый файл содержит:
- `id` - уникальный номер чека
- `source_file` - путь к изображению
- `locale` - локаль (de_DE, pl_PL, ...)
- `store` - информация о магазине
- `metadata` - дата, время, итого, налоги
- `items` - массив товаров (raw_name, qty, price, tax_class...)
- `validation` - данные для checksum (expected_total, discrepancy)
- `notes` - особенности чека

## Статистика

| Метрика | Значение |
|---------|----------|
| **Всего файлов** | **53** |
| Уникальных чеков | 51 (2 дубликата) |
| Локалей | 11 |
| Магазинов | 28 |
| Checksum 0.00 | **100%** |

## Файлы по локалям

### de_DE (Германия) - 32 чека

| ID | Файл | Магазин | Итого |
|----|------|---------|-------|
| 001 | 001_de_DE_lidl_IMG_1292.json | Lidl | 143.37 EUR |
| 013 | 013_de_DE_dm_IMG_1252.json | dm | 8.70 EUR |
| 014 | 014_de_DE_netto_IMG_1256.json | Netto | 47.44 EUR |
| 015 | 015_de_DE_lidl2_IMG_1390.json | Lidl | 18.57 EUR |
| 016 | 016_de_DE_shell_IMG_1391.json | Shell | 14.49 EUR |
| 017 | 017_de_DE_baeckerei_IMG_2034.json | Bäckerei Müller | 5.85 EUR |
| 018 | 018_de_DE_kleins_IMG_3185.json | Kleins Backstube | 4.70 EUR |
| 019 | 019_de_DE_aldi_IMG_1724.json | ALDI SÜD | 72.19 EUR |
| 020 | 020_de_DE_aldi2_IMG_2529.json | ALDI SÜD | 10.17 EUR |
| 024 | 024_de_DE_centershop_IMG_1400.json | CenterShop | 16.70 EUR |
| 026 | 026_de_DE_dm2_IMG_2727.json | dm | 2.80 EUR |
| 027-030 | 027-030_de_DE_edeka*.json | EDEKA (4) | 16.12-34.02 EUR |
| 031-034 | 031-034_de_DE_hit*.json | HIT (4) | 12.81-107.12 EUR |
| 035 | 035_de_DE_penny_IMG_3020.json | Penny | 21.80 EUR |
| **037-052** | **Lidl (16 новых)** | **Lidl** | **4.09-179.24 EUR** |

### pl_PL (Польша) - 7 чеков

| ID | Файл | Магазин | Итого |
|----|------|---------|-------|
| 010 | 010_pl_PL_carrefour_PL_001.json | Carrefour | 254.32 PLN |
| 011 | 011_pl_PL_cropp_PL_002.json | Cropp | 200.97 PLN |
| 012 | 012_pl_PL_orlen_PL_004.json | Orlen | 50.97 PLN |
| 021-023 | 021-023_pl_PL_carrefour*.json | Carrefour (3) | 10.29-86.11 PLN |
| 036 | 036_pl_PL_carrefour_IMG_3033.json | Carrefour | 254.32 PLN |

### es_ES (Испания) - 2 чека

| ID | Файл | Магазин | Итого |
|----|------|---------|-------|
| 003 | 003_es_ES_consum_IMG_3064.json | Consum | 51.15 EUR |
| 025 | 025_es_ES_consum2_IMG_3056.json | Consum | 25.09 EUR |

### pt_PT (Португалия) - 2 чека

| ID | Файл | Магазин | Итого |
|----|------|---------|-------|
| 004 | 004_pt_PT_continente_PT_002.json | Continente | 23.04 EUR |
| **053** | **053_pt_PT_lidl_photo_2025-12-07.json** | **Lidl Lisboa** | **3.37 EUR** |

### Другие локали

| ID | Файл | Локаль | Магазин | Итого |
|----|------|--------|---------|-------|
| 002 | 002_th_TH_7eleven_IMG_2461.json | th_TH | 7-Eleven | 758.25 THB |
| 005 | 005_uk_UA_dniprom_UA_001.json | uk_UA | Dnipro-M | 15305 UAH |
| 006 | 006_cs_CZ_hornbach_cz_001.json | cs_CZ | Hornbach | 1136.00 CZK |
| 007 | 007_bg_BG_billa_BG_001.json | bg_BG | Billa | 26.13 BGN |
| 008 | 008_tr_TR_f33enva_TR_001.json | tr_TR | F33 ENVA | 85.00 TRY |
| 009 | 009_en_IN_nybc_IMG_2475.json | en_IN | NYBC | 450.00 INR |

## Lidl - Самая большая выборка

| Метрика | Значение |
|---------|----------|
| Всего чеков | **18** (16 de_DE + 1 pt_PT + 1 дубликат) |
| Диапазон сумм | 3.37 - 179.24 EUR |
| Филиалы de_DE | 3 (Overath-Vilkerath, St. Augustin, Heiden) |
| Филиалы pt_PT | 1 (Lisboa) |

### Особенности Lidl

- **Pfandrückgabe** - возврат тары до 92 бутылок!
- **Весовые товары** - бананы, мясо, лосось
- **Скидки** - Preisvorteil, RABATT 20%, Rabattaktion
- **Два формата Pfand** - 7% (A) и 19% (B)
- **Разные локали** - de_DE и pt_PT с разным IVA

## Использование

```python
import json
from pathlib import Path

def load_ground_truth(receipt_id: str) -> dict:
    """Загрузить эталонные данные чека."""
    gt_dir = Path("docs/ground_truth")
    for file in gt_dir.glob(f"{receipt_id}_*.json"):
        with open(file) as f:
            return json.load(f)
    raise FileNotFoundError(f"Ground truth for {receipt_id} not found")

def compare_with_ocr_result(ground_truth: dict, ocr_result: dict) -> dict:
    """Сравнить OCR результат с эталоном."""
    differences = {
        "total_match": ground_truth["metadata"]["receipt_total"] == ocr_result.get("total"),
        "items_count_match": len(ground_truth["items"]) == len(ocr_result.get("items", [])),
        "missing_items": [],
        "wrong_prices": []
    }
    return differences
```

## Важные особенности

1. **Дубликаты**: 044 = 043 (IMG_2853 = IMG_2852), 036 = 010 (IMG_3033 = PL_001)
2. **Проблемный чек**: 006 (cs_CZ) - без шапки
3. **Два формата чисел**: 
   - Запятая: Lidl, ALDI, dm, EDEKA... (12,99)
   - Точка: CenterShop, Orlen (12.99)
4. **Инвертированные tax classes**: HIT, Penny (A=19%, B=7%)
5. **Категории на чеке**: Только HIT (031-034)
6. **Pfandrückgabe**: Lidl 052 - возврат 92 бутылок!
7. **Международные Lidl**: de_DE и pt_PT в одной папке
