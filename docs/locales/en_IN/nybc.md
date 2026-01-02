# New York Burrito Company (en_IN)

## Источник
- **Файл:** photo/Mumbai/IMG_2475.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 30-09-2025 07:08

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | NEW YORK BURRITO COMPANY |
| Адрес | 14A, Plot no-89, 14th Floor, Cumba lla H, Mumbai International Airport |
| PIN | 400026, Mumbai, Maharashtra, India |
| GSTIN | 27AAPFN0717N1ZT |
| Валюта | INR |
| Номер чека | NYBC02P122120969 |
| Сотрудник | Vitesh Pawar |
| Способ оплаты | Card |
| Итого | 450.00 |

## Ground Truth таблица

| # | raw_name | qty | unit_price | total_price |
|---|----------|-----|------------|-------------|
| 1 | Tex Mex Veg Bowl (M), Regular | 1.00 | 450.00 | 450.0 |

## Tax Summary (GST)

| Taxable Value | Tax % | Tax Amount | Компонент |
|---------------|-------|------------|-----------|
| 428.57 | 2.50 | 10.71 | CGST |
| 428.57 | 2.50 | 10.71 | SGST |

```
Subtotal:   428.58
Total tax:   21.42
Total:      450.00

Проверка: 428.57 + 21.42 = 449.99 ≈ 450.00 ✓
```

**Расхождение: 0.01** (погрешность округления GST)

## Checksum валидация

```
Товар: 450.00 (включая GST)
Total на чеке: 450.00 ✓
Card: 450.00 ✓
```

**Расхождение: 0.00**

## Паттерн товарной строки

```
          ITEM NAME   QTY  PRICE   Total
---
Tex Mex Veg Bowl (M) ,Regular

NYB023    1.00   450.00     450.0
O
```

### Особенность: Многострочный формат
1. Заголовок таблицы: `ITEM NAME QTY PRICE Total`
2. Название товара на отдельной строке
3. `[код] [qty] [price] [total]` на следующей строке
4. Загадочный "O" на отдельной строке

## Структура чека

### Header
```
** TAX INVOICE **

NEW YORK BURRITO COMPANY

14A, Plot no-89,14th Floor, Cumba
lla H
Mumbai Inetrnational Airport

PIN:400026, Mumbai, Maharashtra,
India
GSTIN: 27AAPFN0717N1ZT
```

### Метаданные
```
Receipt No.: NYBC02P122120969
Employee...: Vitesh Pawar
Date: 30-09-2025 Time.: 07:08
```

### Товары
```
ITEM NAME   QTY  PRICE   Total
---
Tex Mex Veg Bowl (M) ,Regular

NYB023    1.00   450.00     450.0
O
```

### Tax Summary
```
Tax Summary
Taxable value Tax %  Tax Amount
   428.57      2.50     10.71
   428.57      2.50     10.71
Subtotal                 428.58
Total tax                 21.42
Total                    450.00
```

### Footer
```
Card                     450.00
Thanks for shopping! Please visit a
gain.
```

## Особенности

1. **TAX INVOICE** - официальная налоговая накладная
2. **GSTIN** - налоговый идентификатор GST
3. **Табличный заголовок** - ITEM NAME QTY PRICE Total
4. **GST детализация** - CGST + SGST
5. **Английский язык** - легко парсить

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "Tex Mex Veg Bowl (M), Regular" |
| quantity | Да | 1.00 |
| unit_price | Да | 450.00 |
| total_price | Да | 450.0 |
| sku | Да | "NYB023" |
| tax_details | Да | CGST 2.5%, SGST 2.5% |

## GSTIN формат

```
27 AAPFN0717N 1 Z T
│  │          │ │ └─ Checksum
│  │          │ └─── Entity type
│  │          └───── Entity number (1-9, Z, ...)
│  └──────────────── PAN number
└─────────────────── State code (27 = Maharashtra)
```

