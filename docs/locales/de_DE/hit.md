# HIT Verbrauchermarkt (de_DE)

## Источник
- **Файлы:** 
  - photo/GOODS/Hit/IMG_1373.jpeg (большой чек, 107,12 EUR)
  - photo/GOODS/Hit/IMG_1392.jpeg (12,81 EUR)
  - photo/GOODS/Hit/IMG_1453.jpeg (14,99 EUR)
  - photo/GOODS/Hit/IMG_1982.jpeg (52,10 EUR)
- **Дата анализа:** 2025-12-26

## Метаданные

| Поле | Значение |
|------|----------|
| Сеть | HIT Verbrauchermarkt Overath GmbH & |
| Код магазина | HIT 033 Overath / HIT 4033 |
| Адрес | Probsteistraße 18-22, 51491 Overath |
| Часы работы | MO-SA 08:00-22:00 Uhr |
| USt-ID | DE276299025 |
| Валюта | EUR |
| Способ оплаты | Girocard, Visa, EC-Lastschrift |

## УНИКАЛЬНАЯ ОСОБЕННОСТЬ: Категории товаров

HIT группирует товары по **категориям на чеке**:

| Категория | Перевод |
|-----------|---------|
| LEBENSMITTEL | Продукты питания |
| GEKÜHLTE LEBENSMITTEL | Охлажденные продукты |
| TIEFKÜHLKOST | Замороженные продукты |
| GETRÄNKE | Напитки |
| NON FOOD | Непродовольственные товары |
| PFAND/LEERGUT | Залог/Тара |
| THEKE/SBHF | Прилавок/Самообслуживание |
| Bedientheke | Обслуживаемый прилавок |
| WEIN/SPIRITUOSEN/SEKT/CHAMPAGNER | Алкоголь |

## Ground Truth таблица (IMG_1373, выборка)

| Категория | raw_name | code | total_price | tax | F |
|-----------|----------|------|-------------|-----|---|
| THEKE/SBHF | | | | | |
| Bedientheke | Lammkarree fr. | (399) | 6,01 | B | F |
| | Spieße Kreta | (945) | 6,05 | B | F |
| | Schw.Nacken | (527) | 21,83 | B | F |
| | Filetspiess Jalap | (189) | 46,26 | B | F |
| WEIN/SPIRITUOSEN | | | | | |
| *** Discount Preis *** | | | | | |
| | TawnyPortAlVarez | (341) | 12,98 | A | |
| | 2x 6,49 € | | | | |
| | Taylors Ruby Sel | (536) | 13,99 | A | |

## Checksum валидация (все чеки)

| Чек | SUMME[N] | Валидация |
|-----|----------|-----------|
| IMG_1373 | SUMME[3] 107,12 | ✓ |
| IMG_1392 | SUMME[2] 12,81 | ✓ |
| IMG_1453 | SUMME[1] 14,99 | ✓ |
| IMG_1982 | SUMME[10] 52,10 | ✓ |

**Расхождение: 0.00 на всех чеках**

## Паттерн товарной строки

### Тип 1: Обычный товар
```
REWE Feinkostsau    (226)     1,39 B
```

| Компонент | Значение |
|-----------|----------|
| REWE Feinkostsau | Название |
| (226) | Код товара в скобках |
| 1,39 | Цена |
| B | Налоговый класс |

### Тип 2: Товар с прилавка
```
Lammkarree fr.      (399)     6,01 B  F
```
- **F** в конце = Frischtheke (свежий прилавок)

### Тип 3: Скидка
```
*** Discount Preis ***
TawnyPortAlVarez    (341)    12,98 A
      2x 6,49 €
```
- Заголовок `*** Discount Preis ***`
- Детализация `2x 6,49 €` на отдельной строке

### Тип 4: Pfand
```
PFAND/LEERGUT
Pfand 0,25          (005)     0,50 A*
      2x 0,25 €
```
- Категория PFAND/LEERGUT
- **A*** - звездочка = не rabattfähig

## Tax Block

```
Steuer    NETTO [€]   MWST [€] BRUTTO [€]
A=19,00%     22,66       4,31     26,97
B= 7,00%     74,91       5,24     80,15
```

**Важно:** A = 19%, B = 7% (инвертировано по сравнению с другими!)

## Kennzeichenlegende

```
Die mit * gekennzeichneten Artikel sind
nicht rabattfähig. Die wie folgt
gekennzeichneten Artikel sowie die
darauf entfallene MWST werden verkauft
im Namen und Rechnung von:
F=HIT Frische GmbH & Co. KG
```

| Маркер | Значение |
|--------|----------|
| * | Не rabattfähig (не подлежит скидке) |
| F | Продано от имени HIT Frische GmbH |

## Особенности HIT

1. **Категории товаров** - уникальная группировка на чеке!
2. **Код в скобках** - `(226)`, `(399)` и т.д.
3. **SUMME[N]** - N = количество позиций
4. ***** Discount Preis **** - маркер скидки
5. **Инвертированные ставки** - A=19%, B=7%!
6. **F маркер** - товары от HIT Frische
7. **Kennzeichenlegende** - пояснения

## КРИТИЧЕСКОЕ НАБЛЮДЕНИЕ

**Tax class A и B инвертированы!**

| Магазин | A | B |
|---------|---|---|
| Lidl, ALDI, EDEKA | 7% | 19% |
| **HIT** | **19%** | **7%** |

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "Lammkarree fr." |
| product_code | Да | "(399)" |
| quantity | Частично | 2 |
| unit_price | Частично | 6.49 |
| total_price | Да | 12.98 |
| tax_class | Да | "A", "B" |
| category | Уникально! | "THEKE/SBHF" |
| is_fresh | Уникально | true (F маркер) |
| is_discount | Да | "*** Discount Preis ***" |

