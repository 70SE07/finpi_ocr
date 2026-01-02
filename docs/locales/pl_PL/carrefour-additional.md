# Carrefour - дополнительные чеки (pl_PL)

## Источники
- **IMG_3033.jpeg** = IMG_3033 = PL_001 (уже проанализирован)
- **IMG_3036.jpeg** - 1 товар, 10,29 PLN
- **IMG_3047.jpeg** - 2 товара, 18,98 PLN
- **IMG_3048.jpeg** - 5 товаров, 86,11 PLN
- **Дата анализа:** 2025-12-26

## Все чеки из одного магазина

| Поле | Значение |
|------|----------|
| Сеть | CARREFOUR Polska Sp. z o. o. |
| Локация | CH Wileńska |
| Адрес | 03-734 Warszawa ul. Targowa 72 |
| NIP | 937-00-08-168 |

---

## IMG_3036 (1 товар)

| # | raw_name | qty | unit_price | total_price | tax |
|---|----------|-----|------------|-------------|-----|
| 1 | C_MAXI MEAL BAKOMA | 1szt | 10,29 | 10,29 | C |

```
Tax block:
Sprzed. opod. PTU C            10,29
Kwota C 05,00%                  0,49
Podatek PTU                     0,49

SUMA PLN                       10,29
```

**Checksum: 0.00**

---

## IMG_3047 (2 товара)

| # | raw_name | qty | unit_price | total_price | tax |
|---|----------|-----|------------|-------------|-----|
| 1 | A_KOMBUCHA CUDO 500 | 1szt | 14,99 | 14,99 | A |
| 2 | A_MC PAP TOAL NAWIL | 1szt | 3,99 | 3,99 | A |

```
Tax block:
Sprzed. opod. PTU A            18,98
Kwota A 23,00%                  3,55
Podatek PTU                     3,55

SUMA PLN                       18,98
```

**Checksum: 14,99 + 3,99 = 18,98 ✓**

---

## IMG_3048 (5 товаров)

| # | raw_name | qty | unit_price | total_price | tax |
|---|----------|-----|------------|-------------|-----|
| 1 | C_SER KRÓLEWSKI SIE | 1 | 8,05 | 8,05 | C |
| 2 | C_PÓŁBAGIETKA Z SE | 2 | 2,19 | 4,38 | C |
| 3 | C_NAPÓJ AYRAN 330ML | 2 | 3,85 | 7,70 | C |
| 4 | C_MOWI ŁOSOS WĘDZ. | 1 | 32,99 | 32,99 | C |
| 5 | C_MOWI ŁOSOS WĘDZ. | 1 | 32,99 | 32,99 | C |

```
Tax block:
Sprzed. opod. PTU C            86,11
Kwota C 05,00%                  4,10
Podatek PTU                     4,10

SUMA PLN                       86,11
```

**Checksum: 8,05 + 4,38 + 7,70 + 32,99 + 32,99 = 86,11 ✓**

---

## Особенность: Donateo

В IMG_3048 есть блок **NIEFISKALNY** с благотворительным пожертвованием:

```
Mikro-Datek:              PLN 3,87
Razem:                    PLN 89,98
...
Przekazano kwotę 3,87 PLN na Fundacje
Donateo - Fundacja Na Ratunek
```

Это дополнительное пожертвование, **не влияет на SUMA**.

---

## Сводка по всем чекам Carrefour

| Чек | Товаров | SUMA | Tax | Checksum |
|-----|---------|------|-----|----------|
| PL_001 | ~28 | 254,32 | A+C | 0.00 ✓ |
| IMG_3036 | 1 | 10,29 | C | 0.00 ✓ |
| IMG_3047 | 2 | 18,98 | A | 0.00 ✓ |
| IMG_3048 | 5 | 86,11 | C | 0.00 ✓ |

**Всего: 4 чека, все с расхождением 0.00**

---

## Подтверждение паттернов

1. **Префикс категории** - `A_`, `C_` всегда присутствует
2. **Формат** - `[qty]szt*[price]= [total] [tax]` или `[qty]*[price]= [total] [tax]`
3. **Tax classes** - A (23%), C (5%)
4. **PAYBACK** - бонусная программа
5. **NIEFISKALNY** - нефискальный блок (пожертвования)

