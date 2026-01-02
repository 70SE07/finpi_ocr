# Lidl - второй пример (de_DE)

## Источник
- **Файл:** data/input/IMG_1390.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 14.08.25 15:14

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | Lidl |
| Адрес | Steinhauser Auel 1, 51491 Overath-Vilkerath |
| Валюта | EUR |
| Способ оплаты | Kartenzahlung girocard |
| Итого | 18,57 EUR |
| Скидка | 2,00 EUR |

## Ground Truth таблица

| # | raw_name | qty | unit_price | total_price | tax |
|---|----------|-----|------------|-------------|-----|
| 1 | Dattelcherrytomaten | 1 | 1,99 | 1,99 | A |
| 2 | Bio Gurken | 1 | 1,19 | 1,19 | A |
| 3 | Ayran Joghurtgetränk | 1 | 1,49 | 1,49 | A |
| 4 | Kefir | 5 | 0,89 | 4,45 | A |
| 5 | Dovgan Fam.33% Fett | 5 | 2,29 | 11,45 | A |
| 6 | Preisvorteil | - | - | -2,00 | - |

## Checksum валидация

```
1,99 + 1,19 + 1,49 + 4,45 + 11,45 - 2,00 = 18,57

zu zahlen на чеке: 18,57 EUR ✓
```

**Расхождение: 0.00**

## Паттерн товарной строки

### Тип 1: Простой товар
```
Dattelcherrytomaten                      EUR     1,99 A
Bio Gurken                               EUR     1,19 A
Ayran Joghurtgetränk                     EUR     1,49 A
```

### Тип 2: Товар с количеством
```
Kefir                0,89 x    5                 4,45 A
Dovgan Fam.33% Fett  2,29 x    5                11,45 A
```
**Формат:** `[название] [unit_price] x [qty] [total] [tax]`

### Тип 3: Скидка
```
Preisvorteil                                    -2,00
```

## Tax Block

```
MWST%    MWST +    Netto   =  Brutto
A  7%    1,21     17,36       18,57
Summe    1,21     17,36       18,57
```

**Проверка:**
- 17,36 × 1.07 = 18,58 ≈ 18,57 ✓
- 17,36 × 0.07 = 1,22 ≈ 1,21 ✓

**Примечание:** Все товары 7% (A) - продукты питания.

## Сравнение с первым Lidl (IMG_1292)

| Признак | IMG_1292 | IMG_1390 |
|---------|----------|----------|
| Tax A | 19% | 7% |
| Preisvorteil | Нет | Да (-2,00) |
| Формат qty | Одинаковый | Одинаковый |
| Весовые | Да | Нет |

**Вывод:** Tax class A в Lidl может быть и 19% и 7% - зависит от категории товаров!

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "Kefir" |
| quantity | Да | 5 |
| unit_price | Да | 0.89 |
| total_price | Да | 4.45 |
| tax_class | Да | "A" |
| is_discount | Да | true (Preisvorteil) |

## Gesamter Preisvorteil

```
Gesamter Preisvorteil                   2,00
```

Это общая экономия по акциям - аналог `#ТИ СПЕСТИ#` в Болгарии.

