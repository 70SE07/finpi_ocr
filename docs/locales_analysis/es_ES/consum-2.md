# Consum - второй пример (es_ES)

## Источник
- **Файл:** photo/GOODS/Consum/IMG_3056.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 11.11.2025 17:30

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | Consum S.COOP.V. |
| Магазин | 650 - Torrevieja CC Punta Marina |
| Телефон | 966799780 |
| Адрес | Avd. Alginet, nº 1, Silla |
| N.I.F. | F46078986 |
| Номер чека | C:0650 07/000025 |
| Сотрудник | PILAR |
| Валюта | EUR |
| Способ оплаты | Efectivo (наличные) |
| Итого | 25,09 EUR |
| Получено | 40,00 EUR |
| Сдача | 14,91 EUR |

## Ground Truth таблица

| # | qty | raw_name | total_price |
|---|-----|----------|-------------|
| 1 | 1 | ZUMO R.EX. 500 | 3,69 |
| 2 | - | MANDARINA GRANEL | 0,68 |
| 3 | 1 | MANZANA ROYAL GALA | 1,09 |
| 4 | 1 | MANGO | 1,55 |
| 5 | 1 | LECHUGA ROMANA CON | 1,15 |
| 6 | - | PAN ALTO CONTE.PROT | 1,89 |
| 7 | 1 | QU.GOUDA LON. 200GR | 2,09 |
| 8 | - | CREMA Q.BRIE TRUFA | 1,75 |
| 9 | - | TIRAMISU 2X80 CONSU | 1,25 |
| 10 | 1 | G.CHOCO PAUSE MILKA | 3,25 |
| 11 | 1 | MINI BURGER NEGRO | 1,39 |
| 12 | - | SNATTS CON QUESO | 1,13 |
| 13 | 1 | PALITOS QUESO | 0,71 |
| 14 | 1 | BURN PACK-4 | 3,32 |
| 15 | 1 | BOLSA COMPRA RECICL | 0,15 |

## Checksum валидация

```
3,69 + 0,68 + 1,09 + 1,55 + 1,15 + 1,89 + 2,09 + 1,75 + 1,25 + 3,25 + 1,39 + 1,13 + 0,71 + 3,32 + 0,15 = 25,09

Total factura на чеке: 25,09 ✓
```

**Расхождение: 0.00**

## Проверка сдачи

```
Efectivo: 40,00
Total: 25,09
Cambio: 40,00 - 25,09 = 14,91 ✓
```

## FACTURA SIMPLIFICADA - Tax Block

```
FACTURA SIMPLIFICADA
Base   IVA  Cuota  Importe
5,35  10,00  0,54    5,89
2,88  21,00  0,59    3,47
15,14  4,00  0,59   15,73
```

| Base | IVA % | Cuota | Importe |
|------|-------|-------|---------|
| 5,35 | 10% | 0,54 | 5,89 |
| 2,88 | 21% | 0,59 | 3,47 |
| 15,14 | 4% | 0,59 | 15,73 |

**Сумма:** 5,89 + 3,47 + 15,73 = 25,09 ✓

## Три ставки IVA!

| Ставка | Применение |
|--------|------------|
| 4% | Базовые продукты (хлеб, фрукты, овощи) |
| 10% | Продукты питания |
| 21% | Непродовольственные товары |

## Паттерн товарной строки

```
     UND        PVP
KG  ARTICULO   €/KG  TOTAL
1 ZUMO R.EX. 500          3,69
  MANDARINA GRANEL        0,68
1 MANZANA ROYAL GALA      1,09
```

| Компонент | Описание |
|-----------|----------|
| 1 | Количество (если указано) |
| ZUMO R.EX. 500 | Название |
| 3,69 | Цена |

**Особенность:** Некоторые товары без qty (весовые или implicit 1).

## MundoConsum

```
Con la Tarjeta MundoConsum esta compra
acumularía en tu Cheque Regalo 0,89 €
```

Бонусная программа - 0,89 EUR накоплено.

## Сравнение двух чеков Consum

| Признак | IMG_3064 | IMG_3056 |
|---------|----------|----------|
| Товаров | ~20 | 15 |
| Итого | 51,15 | 25,09 |
| IVA ставки | 1 | 3 (4%, 10%, 21%) |
| Оплата | Карта | Наличные |
| Tax block | Нет | FACTURA SIMPLIFICADA |

## Выводы для DTO

| Поле | Присутствует | Пример |
|------|--------------|--------|
| raw_name | Да | "ZUMO R.EX. 500" |
| quantity | Частично | 1 |
| total_price | Да | 3.69 |
| tax_rate | В tax block | 4%, 10%, 21% |

