# Consum (es_ES)

## Источник
- **Файл:** photo/GOODS/Consum/IMG_3064.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 28.10.2025 18:40

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | Consum (Juntos es cooperativa) |
| Филиал | 190 - Orihuela Los Altos |
| Телефон | 965327229 |
| Номер чека | C:0190 07/000023 715221 |
| Валюта | EUR |
| Способ оплаты | Tarj. Crédito |
| Итого | 51,15 EUR |

## Структура чека

```
┌─────────────────────────────────────────┐
│ consum                                  │
│ Juntos es cooperativa                   │
│ 190 - Orihuela Los Altos               │
│ Tlf.965327229                          │
├─────────────────────────────────────────┤
│ C:0190 07/000023 28.10.2025 18:40      │
├─────────────────────────────────────────┤
│ UND    ARTICULO       PVP  €/KG  TOTAL │
│ KG                                      │
├─────────────────────────────────────────┤
│ ITEMS (22 позиции)                      │
│ 1  TOMATE RAF ASURCAD           1,06   │
│ ...                                     │
│ 0,580  GAMBÓN GRANDE            7,51   │
│ ...                                     │
├─────────────────────────────────────────┤
│ Total factura:                 51,15   │
│ IMPORTE A ABONAR               51,15   │
│ Tarj. Crédito                  51,15   │
│ Cambio                          0,00   │
├─────────────────────────────────────────┤
│ Con la Tarjeta MundoConsum...          │
│ -------Venta Tarjeta Bancaria-------   │
│ DEBIT MASTERCARD                        │
└─────────────────────────────────────────┘
```

## Паттерны товарных строк

### Тип 1: Простой товар (qty=1)
```
Qty  Название                         Total
 1   TOMATE RAF ASURCAD                1,06
 1   COMBIN. SETAS 200                 2,99
```
- Qty в НАЧАЛЕ строки
- Нет отдельного unit_price
- unit_price = total_price

### Тип 2: Штучный товар с множителем
```
Qty  Название              Unit_Price  Total
 2   BAT.00% PROTE.CACAO      1,75     3,50
 2   CCOLA ZERO CHERRY        0,92     1,84
```
- Unit price указан между названием и total
- Math: 2 * 1,75 = 3,50

### Тип 3: Весовой товар
```
Qty      Название                      Total
0,580    GAMBÓN GRANDE                  7,51
```
- Qty с запятой (не точкой!)
- Нет отдельной строки с unit_price (€/kg)
- Колонка €/KG в заголовке, но данные пустые

## Ground Truth таблица

| # | qty | raw_name | unit_price | total_price | is_discount |
|---|-----|----------|------------|-------------|-------------|
| 1 | 1 | TOMATE RAF ASURCAD | 1,06 | 1,06 | false |
| 2 | 1 | COMBIN. SETAS 200 | 2,99 | 2,99 | false |
| 3 | 1 | BONIATO AL VAPOR | 1,99 | 1,99 | false |
| 4 | 1 | MAXI VAR.CONSUM 350 | 1,99 | 1,99 | false |
| 5 | 1 | LECHUGA ROMANA CON | 1,15 | 1,15 | false |
| 6 | 1 | HIERBABUENA 20 GR | 1,25 | 1,25 | false |
| 7 | 1 | PICADA DE AJO Y PER | 1,49 | 1,49 | false |
| 8 | 1 | BAGUETTE 220 GR. | 0,58 | 0,58 | false |
| 9 | 0,580 | GAMBÓN GRANDE | - | 7,51 | false |
| 10 | 1 | JAMON GR CONSUM 150 | 2,99 | 2,99 | false |
| 11 | 1 | PALETA CEBO BOADAS | 5,65 | 5,65 | false |
| 12 | 2 | BAT.00% PROTE.CACAO | 1,75 | 3,50 | false |
| 13 | 2 | BAT.00% PROTE.VAINI | 1,75 | 3,50 | false |
| 14 | 1 | HUEVO CAMPERO L 10U | 3,78 | 3,78 | false |
| 15 | 1 | AC MANZ CONUM 210 G | 1,65 | 1,65 | false |
| 16 | 1 | ALCAPARRAS CONSUM80 | 1,35 | 1,35 | false |
| 17 | 1 | PMTO PIQUI.CONSUM | 1,19 | 1,19 | false |
| 18 | 1 | SALSA C/SOJA HEINZ | 2,99 | 2,99 | false |
| 19 | 2 | CCOLA ZERO CHERRY | 0,92 | 1,84 | false |
| 20 | 1 | COCA-COLA ZERO 0,50 | 1,15 | 1,15 | false |
| 21 | 1 | B.ENERG.BURN 0,50L | 1,25 | 1,25 | false |
| 22 | 2 | BOLSA COMPRA RECICL | 0,15 | 0,30 | false |

## Checksum валидация

```
Сумма товаров:
1,06 + 2,99 + 1,99 + 1,99 + 1,15 + 1,25 + 1,49 + 0,58 + 
7,51 + 2,99 + 5,65 + 3,50 + 3,50 + 3,78 + 1,65 + 1,35 + 
1,19 + 2,99 + 1,84 + 1,15 + 1,25 + 0,30 = 51,15

Total factura на чеке: 51,15 ✓
```

**Расхождение: 0.00**

## Выводы для DTO

| Поле | Присутствует | Пример | Комментарий |
|------|--------------|--------|-------------|
| raw_name | Да | "TOMATE RAF ASURCAD" | UPPERCASE |
| quantity | Да | 0.580 | Float с запятой |
| unit | Частично | kg (только весовые) | Колонка в заголовке |
| unit_price | Частично | 1,75 | Только если qty > 1 |
| total_price | Да | 3,50 | Всегда |
| tax_class | Нет | - | Нет tax block |
| is_discount | Нет (на этом чеке) | - | - |

## Особенности для парсинга

1. **Qty в начале строки** - числа слева
2. **Запятая как десятичный разделитель** в qty (0,580)
3. **Весовой товар** - только qty и total, без unit_price
4. **Нет tax block** - только общий итог
5. **Заголовки колонок** - можно использовать для определения структуры

