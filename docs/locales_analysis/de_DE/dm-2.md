# dm-drogerie markt - второй пример (de_DE)

## Источник
- **Файл:** photo/GOODS/DM/IMG_2727.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 05.11.2025 10:42

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | dm-drogerie markt |
| Адрес | Steinhofplatz 1, 51491 Overath |
| Телефон | 02206/9050520 |
| Номер кассы | D55F/1 |
| Чек | 328755/12 |
| Steuer-Nr. | 34092/30007 |
| Валюта | EUR |
| Способ оплаты | KARTENZAHLUNG EUR |
| Итого | 2,80 EUR |

## Ground Truth таблица

| # | raw_name | total_price | tax | note |
|---|----------|-------------|-----|------|
| 1 | Copyservice | 1,00 | 1 | Услуга |
| 2 | Lemonaid Limette 330ml+0,25Pf | 1,55 | 1 | Напиток |
| 3 | Einwegpfand | 0,25 | §1 | Pfand! |

## Checksum валидация

```
1,00 + 1,55 + 0,25 = 2,80

SUMME EUR на чеке: 2,80 ✓
```

**Расхождение: 0.00**

## Паттерн товарной строки

```
Copyservice                  1,00  1
Lemonaid Limette 330ml+0,25Pf  1,55  1
Einwegpfand                  0,25 §1
```

## УНИКАЛЬНО: §1 для Pfand!

```
Einwegpfand                  0,25 §1
```

**§1** - специальный код для Einwegpfand (одноразовый залог) в dm!

Это соответствует немецкому закону о залоге (Pfandgesetz).

## Tax Block

```
MwSt-Satz    Brutto    Netto      MwSt
1=19,00%      2,80      2,35      0,45
§: Für diese Artikel werden keine Rabatte
   vergeben
```

**Проверка:**
- Brutto: 2,80
- Netto: 2,35
- MwSt: 0,45
- 2,35 × 0.19 = 0,45 ✓

## Особенности

1. **Copyservice** - услуга копирования в dm
2. **+0,25Pf** - Pfand включен в название напитка!
3. **Einwegpfand** - отдельная строка для залога
4. **§1** - специальный налоговый код для Pfand
5. **"keine Rabatte vergeben"** - товары не подлежат скидке

## Сравнение двух чеков dm

| Признак | IMG_1252 | IMG_2727 |
|---------|----------|----------|
| Товары | Детские товары | Услуга + напиток |
| Pfand | Нет | Да (§1) |
| Tax class | 1 | 1, §1 |
| Итого | 8,70 | 2,80 |

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "Lemonaid Limette 330ml+0,25Pf" |
| quantity | Нет | - |
| total_price | Да | 1.55 |
| tax_class | Да | "1" или "§1" |
| is_pfand | Да | true (§1) |

