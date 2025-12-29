# Continente (pt_PT)

## Источник
- **Файл:** data/input/PT_002.jpeg
- **Дата анализа:** 2025-12-26
- **Дата чека:** 09/11/2025 13:10

## Метаданные чека

| Поле | Значение |
|------|----------|
| Сеть | Modelo Continente Hipermercados SA |
| Филиал | CBD General Rocadas |
| NIF | PT502011475 |
| Номер | FS LM0001/734800 |
| Тип | Fatura Simplificada Original |
| Валюта | EUR |
| Способ оплаты | Cartao Credito (VISA) |
| Итого | 23,04 EUR |
| Скидки | 4,00 EUR |

## Структура чека

```
┌─────────────────────────────────────────┐
│ CBD General Rocadas                     │
│ Modelo Continente Hipermercados SA      │
│ 210117601                               │
│ NIF: PT502011475...                     │
│ Fatura Simplificada Original            │
│ Nr:FS LM0001/734800 09/11/2025 13:10   │
├─────────────────────────────────────────┤
│ IVA  DESCRICAO                   VALOR  │
│ ----------------------------------------│
│ Laticinios/Beb. Veg.:                  │
│ (A)  OVOS CLASSE M/L RUBY 1DZ    3,29  │
│                                         │
│ Bens Essenciais:                       │
│ (A)  AZEITE VE RESERVA GALLO..   6,99  │
│      POUPANCA                   -4,00  │
│                                         │
│ Charcutaria&Queijos:                   │
│ (A)  BURRATA DE VACA CNT 200G    2,79  │
│                                         │
│ Frutas e Legumes:                      │
│ (A)  DIOSPIRO                    8,78  │
│      2,200 X 3,99                       │
│ (A)  ESPINAFRE RESIDUO ZERO..    1,19  │
├─────────────────────────────────────────┤
│ TOTAL A PAGAR                   23,04  │
│ Cartao Credito                  23,04  │
│ ----------------------------------------│
│ Total de descontos e poupancas   4,00  │
├─────────────────────────────────────────┤
│      %IVA   Total Liq.   IVA    Total  │
│ (A)  6,00%    21,74     1,30   23,04   │
├─────────────────────────────────────────┤
│ EE/*Processado por programa...         │
│ ATCUD:JF9NCNTM-734800                  │
│ [QR код]                                │
│ BOM DIA GENERAL ROCA                   │
│ Terminal, VISA INTERNACIONAL           │
│ ...                                     │
└─────────────────────────────────────────┘
```

## Паттерны товарных строк

### Тип 1: Простой товар
```
(A)  OVOS CLASSE M/L RUBY 1DZ           3,29
```
- Tax class (A) в начале
- Название
- Total справа

### Тип 2: Товар со скидкой
```
(A)  AZEITE VE RESERVA GALLO 0.75L      6,99
     POUPANCA                          -4,00
```
- Скидка на СЛЕДУЮЩЕЙ строке
- Ключевое слово "POUPANCA"
- **Внимание:** цена 6,99 - это ДО скидки или ПОСЛЕ? 
  - По tax block: Total Liq. = 21,74, что означает цены УЖЕ со скидкой
  - Значит 6,99 - 4,00 = 2,99 (реальная цена)

### Тип 3: Весовой товар
```
(A)  DIOSPIRO                           8,78
     2,200 X 3,99
```
- Total на первой строке
- Детализация (qty X unit_price) на ВТОРОЙ строке
- Math: 2,200 * 3,99 = 8,778 ≈ 8,78

## Ground Truth таблица

| # | tax | category | raw_name | qty | unit_price | total_price | is_discount |
|---|-----|----------|----------|-----|------------|-------------|-------------|
| 1 | A | Laticinios/Beb. Veg. | OVOS CLASSE M/L RUBY 1DZ | 1 | 3,29 | 3,29 | false |
| 2 | A | Bens Essenciais | AZEITE VE RESERVA GALLO 0.75L | 1 | 6,99 | 6,99 | false |
| 3 | - | - | POUPANCA | - | - | -4,00 | true |
| 4 | A | Charcutaria&Queijos | BURRATA DE VACA CNT 200G | 1 | 2,79 | 2,79 | false |
| 5 | A | Frutas e Legumes | DIOSPIRO | 2,200 | 3,99 | 8,78 | false |
| 6 | A | Frutas e Legumes | ESPINAFRE RESIDUO ZERO 125GR | 1 | 1,19 | 1,19 | false |

## Checksum валидация

### По tax block
```
Tax Block:
(A) 6,00%: Total Liq. = 21,74, IVA = 1,30, Total = 23,04

Проверка IVA: 21,74 * 0,06 = 1,3044 ≈ 1,30 ✓
Проверка Total: 21,74 + 1,30 = 23,04 ✓
```

### По товарам
```
Сумма товаров (gross): 3,29 + 6,99 + 2,79 + 8,78 + 1,19 = 23,04
Но скидка -4,00 показана отдельно...

Интерпретация: "Total de descontos e poupancas: 4,00" - 
это информация о том, сколько клиент СЭКОНОМИЛ.
Цены товаров УЖЕ включают скидку (6,99 это цена со скидкой, 
оригинальная цена была 10,99).

Итого: 3,29 + 6,99 + 2,79 + 8,78 + 1,19 = 23,04 ✓
```

**Расхождение: 0.00**

## Выводы для DTO

| Поле | Присутствует | Пример | Комментарий |
|------|--------------|--------|-------------|
| raw_name | Да | "DIOSPIRO" | |
| quantity | Частично | 2,200 | Только весовые |
| unit | Нет | - | Подразумевается kg |
| unit_price | Частично | 3,99 | Только весовые |
| total_price | Да | 8,78 | Всегда |
| tax_class | Да | "A" | Перед названием |
| is_discount | Да | true | POUPANCA |
| category | Да | "Frutas e Legumes" | Уникально для pt_PT |

## Особенности для парсинга

1. **Tax class (A)** в начале строки
2. **Категории** как разделители между группами товаров
3. **POUPANCA** - скидка, но цены УЖЕ со скидкой
4. **Весовой товар** - детализация на ВТОРОЙ строке (2,200 X 3,99)
5. **Tax block** - надежный источник для валидации
6. **NIF** - налоговый идентификатор

