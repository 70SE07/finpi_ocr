# EDEKA (de_DE)

## Источник
- **Файлы:** 
  - photo/GOODS/Edeka/IMG_1331.jpeg (2 товара)
  - photo/GOODS/Edeka/IMG_1525.jpeg (7 товаров)
  - photo/GOODS/Edeka/IMG_1896.jpeg (5 товаров)
  - photo/GOODS/Edeka/IMG_1931.jpeg (14 товаров)
- **Дата анализа:** 2025-12-26

## Метаданные

| Поле | Значение |
|------|----------|
| Сеть | EDEKA Felbecker |
| Адрес | Pilgerstr. 69-71, 51491 Overath-Marialinden |
| Телефон | 02206 / 912784 |
| Сайт | www.edeka.de |
| Steuernummer | 204/5085/2941 |
| Валюта | EUR |
| Способ оплаты | EC-Cash, Mastercard, girocard |

## Ground Truth таблица (IMG_1331)

| # | raw_name | total_price | tax |
|---|----------|-------------|-----|
| 1 | Beleg Frischfleisch + Geflüg | 13,23 | - |
| 2 | Leerdamm.Delacreme | 2,89 | A |

```
Posten: 2
SUMME  €  16,12
```

## Ground Truth таблица (IMG_1525)

| # | raw_name | total_price | tax |
|---|----------|-------------|-----|
| 1 | Red Bull 0,25l | 0,99 | BW |
| 2 | Pfand | 0,25 | +B |
| 3 | G&G Butterkäse | 2,79 | A |
| 4 | G&G Gef.Mortadella | 1,29 | A |
| 5 | G&G Mortadella | 1,29 | A |
| 6 | Herz.M.Pfl.Tomaten | 1,99 | A |
| 7 | G&G Sandw.Toast V. | 1,09 | A |

```
Posten: 7
SUMME  €  9,69
```

## ВАЖНО: Расширенные tax codes

| Код | Значение |
|-----|----------|
| A | 7% (продукты) |
| B | 19% (непродовольственные) |
| **BW** | ? (возможно Brauerei/Wein) |
| **AW** | ? (возможно Alkohol/Wein) |
| **+B** | 19% Pfand (залог) |

## Ground Truth таблица (IMG_1931)

| # | raw_name | qty | unit_price | total_price | tax |
|---|----------|-----|------------|-------------|-----|
| 1 | Magnum Mandel | 1 | 2,99 | 2,99 | AW |
| 2 | Mars Eisriegel | 1 | 3,49 | 3,49 | A |
| 3 | Tena Lights Einl. | 1 | 2,99 | 2,99 | B |
| 4 | Dov.Kondensm1 | 2 | 2,09 | 4,18 | A |
| 5 | Dovg.Kondensm | 2 | 1,79 | 3,58 | A |
| ... | ... | ... | ... | ... | ... |

**Формат qty:** `2,09 € x 2` - цена перед количеством!

## Checksum валидация (все чеки)

| Чек | Сумма позиций | SUMME | Расхождение |
|-----|---------------|-------|-------------|
| IMG_1331 | 16,12 | 16,12 | 0.00 ✓ |
| IMG_1525 | 9,69 | 9,69 | 0.00 ✓ |
| IMG_1896 | 8,81 | 8,81 | 0.00 ✓ |
| IMG_1931 | 34,02 | 34,02 | 0.00 ✓ |

## Паттерны товарных строк

### Тип 1: Простой товар
```
G&G Butterkäse                     2,79 A
```

### Тип 2: Pfand
```
Pfand                              0,25 +B
```

### Тип 3: Товар с количеством
```
Dov.Kondensm1  2,09 € x   2        4,18 A
```
**Формат:** `[название] [unit_price] € x [qty] [total] [tax]`

## Tax Block

```
MwSt    NETTO     MwSt    UMSATZ
A  7%   15,07     1,05    16,12
```

или

```
MwSt    NETTO     MwSt    UMSATZ
A   7%   7,90     0,55     8,45
B  19%   1,04     0,20     1,24
```

## Особенности EDEKA

1. **Posten: N** - количество позиций в чеке
2. **Расширенные tax codes** - A, B, AW, BW, +B
3. **Pfand с +** - `+B` для залога
4. **Формат qty** - цена ПЕРЕД количеством
5. **** Kundenbeleg **` - блок терминала
6. **PAYBACK** - бонусная программа

## Сравнение с другими супермаркетами

| Признак | EDEKA | Lidl | ALDI | HIT |
|---------|-------|------|------|-----|
| SKU | Нет | Нет | Да | Да (код) |
| Posten | Да | Нет | Нет | SUMME[N] |
| Tax codes | A,B,AW,BW,+B | A,B,M | A,B | A,B,F |
| Pfand marker | +B | M | B | A* |

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "G&G Butterkäse" |
| quantity | Частично | 2 |
| unit_price | Частично | 2.09 |
| total_price | Да | 4.18 |
| tax_class | Да | "A", "B", "AW", "BW", "+B" |

