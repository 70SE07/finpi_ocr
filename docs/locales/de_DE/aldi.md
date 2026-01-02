# ALDI SÜD (de_DE)

## Источник
- **Файлы:** 
  - photo/GOODS/Aldi/IMG_1724.jpeg (большой чек)
  - photo/GOODS/Aldi/IMG_2529.jpeg (маленький чек)
- **Дата анализа:** 2025-12-26

## Метаданные (IMG_1724)

| Поле | Значение |
|------|----------|
| Сеть | ALDI SÜD |
| Адрес | Wiesenauel 1, 51491 Overath |
| UST-ID-Nr. | DE 813192189 |
| Часы работы | Mo - Sa: 8:00 Uhr - 20:00 Uhr |
| Валюта | EUR |
| Способ оплаты | Kartenzahlung girocard |
| Итого | 72,19 EUR |
| Слоган | "ALDI SÜD - Gutes für alle." |

## Ground Truth таблица (IMG_1724, выборка)

| # | sku | raw_name | qty | unit_price | total_price | tax |
|---|-----|----------|-----|------------|-------------|-----|
| 1 | 826945 | Allzwecktragetasch | 1 | 0,99 | 0,99 | B |
| 2 | 826945 | Allzwecktragetasch | 1 | 0,99 | 0,99 | B |
| 3 | 2938 | Zucker - Raffinade | 1 | 0,89 | 0,89 | A |
| 4 | 728573 | Gouda 400g | 1 | 2,99 | 2,99 | A |
| 5 | 807611 | Bio FT Lose Banane | 0,834 | 1,99/kg | 1,66 | A |
| ... | ... | ... | ... | ... | ... | ... |
| - | - | Rabatt 30,0% | - | - | -1,65 | A |
| - | 6205 | Pfand | 1 | 0,25 | 0,25 | B |

## Checksum валидация (IMG_1724)

```
Summe на чеке: 72,19 EUR ✓
Tax block:
  A 07,0% Netto 63,34 MwSt 4,43 → Brutto 67,77
  B 19,0% Netto  3,71 MwSt 0,71 →  Brutto 4,42
  Total: 67,77 + 4,42 = 72,19 ✓
```

**Расхождение: 0.00**

## Checksum валидация (IMG_2529)

```
715057 Eier Bodenh. 18er    3,39 A (x3)
3,39 × 3 = 10,17

Summe на чеке: 10,17 EUR ✓
Tax: A 07,0% Netto 9,50 MwSt 0,67 → 10,17 ✓
```

**Расхождение: 0.00**

## Паттерны товарных строк

### Тип 1: Простой товар
```
826945 Allzwecktragetasch        0,99 B
```
| Компонент | Значение |
|-----------|----------|
| 826945 | SKU (артикул) |
| Allzwecktragetasch | Название |
| 0,99 | Цена |
| B | Налоговый класс |

### Тип 2: Весовой товар
```
807611 Bio FT Lose Banane
    0,834 kg x      1,99 EUR/kg         1,66 A
```
- SKU + название на первой строке
- qty × price = total + tax на второй строке

### Тип 3: Скидка в процентах
```
733244 F&G Häh Min.schn           5,49 A
Rabatt      30,0%                -1,65
```
- **Rabatt [процент]%** - уникальный формат!
- Процент скидки явно указан

### Тип 4: Pfand (залог)
```
6205 Pfand                        0,25 B
```

## Tax Block

```
              Summe           72,19
          girocard    EUR    72,19

A  07,0% Netto    63,34    MwSt    4,43
B  19,0% Netto     3,71    MwSt    0,71
```

## Особенности ALDI SÜD

1. **SKU перед названием** - 4-6 цифр
2. **Весовые на 2 строки** - формат `qty kg x price EUR/kg`
3. **Rabatt в процентах** - `Rabatt 30,0%` + сумма
4. **Tax classes** - A (7%), B (19%)
5. **Pfand** - залог за тару, класс B
6. **Слоган** в футере чека

## Сравнение с другими дискаунтерами

| Признак | ALDI | Lidl | Netto | Penny |
|---------|------|------|-------|-------|
| SKU | Да | Нет | Нет | Нет |
| Rabatt % | Да | Нет | Нет | Нет |
| Весовые | 2 строки | 2 строки | 3 строки | 2 строки |
| Preisvorteil | Rabatt | Preisvorteil | - | - |

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| sku | Да | "826945" |
| raw_name | Да | "Allzwecktragetasch" |
| quantity | Да | 0.834 |
| unit | Да | "kg" |
| unit_price | Да | 1.99 |
| total_price | Да | 1.66 |
| tax_class | Да | "A" или "B" |
| discount_percent | Уникально! | 30.0 |

