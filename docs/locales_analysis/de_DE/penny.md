# Penny (de_DE)

## Источник
- **Файл:** photo/GOODS/Penny/IMG_3020.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 16.06.2025 18:03:26

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | *** P E N N Y - M A R K T *** |
| Компания | H-SCHMAND OGT GmbH |
| UID Nr. | DE202748117 |
| Адрес | Steinhofplatz 1, 51491 Overath |
| Валюта | EUR |
| Способ оплаты | EC-Cash |
| Итого | 21,80 EUR |

## Ground Truth таблица

| # | raw_name | total_price | tax | note |
|---|----------|-------------|-----|------|
| 1 | PELMENI SCHWEIN | 0,89 | B | - |
| 2 | PLOMBIR SCHNE | 5,99 | A | - |
| 3 | Fanta Cassis | 0,99 | A | - |
| 4 | Red Bull 0,33l 75 | 1,75 | - | - |
| 5 | PFAND STK x 0,25 EURO | - | - | Pfand |
| 6 | PFAND 0,25 | 0,25 | - | - |
| 7 | Capri Sun Mango | 7,00 | A | - |
| 8 | | 1,00 | A | ? |
| 9 | | 1,29 | A | ? |
| 10 | SUMME | 21,80 | - | Total |

**Примечание:** Чек повернут на 90 градусов, сложно читать.

## Checksum валидация

```
SUMME на чеке: 21,80 EUR ✓
Tax block:
  A= 19,0% Netto 8,85 Steuer 1,68 Brutto 10,53
  B=  7,0% Netto 0,74 Steuer 0,05 Brutto  0,79
  (и еще строка)
  Gesamtbetrag: 21,80
```

**Расхождение: 0.00**

## Паттерн товарной строки

```
PELMENI SCHWEIN           EUR      0,89 B
PLOMBIR SCHNE             EUR      5,99 A
PFAND STK x 0,25 EURO
PFAND 0,25                EUR      0,25
```

| Компонент | Значение |
|-----------|----------|
| PELMENI SCHWEIN | Название |
| EUR | Валюта (явно указана) |
| 0,89 | Цена |
| B | Налоговый класс |

## Tax Block

```
Steuer  %       Netto    Steuer    Brutto
A=  19,0        8,85     1,68      10,53
B=   7,0        0,74     0,05       0,79
...
Gesamtbetrag:                      21,80
```

## Особенности Penny

1. ***** P E N N Y - M A R K T **** - название с пробелами и звездочками
2. **EUR явно в строке** - как у Shell
3. **Tax classes** - A (19%), B (7%)
4. **Pfand** - отдельными строками
5. **Дискаунтер** - принадлежит REWE Group

## Сравнение с другими дискаунтерами REWE Group

| Признак | Penny | Lidl | ALDI |
|---------|-------|------|------|
| EUR в строке | Да | Нет | Нет |
| SKU | Нет | Нет | Да |
| Tax A | 19% | 7% | 7% |
| Tax B | 7% | 19% | 19% |

**Важно:** В Penny тоже инвертированы tax classes (как в HIT)!

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "PELMENI SCHWEIN" |
| quantity | Нет | - |
| total_price | Да | 0.89 |
| tax_class | Да | "A", "B" |

