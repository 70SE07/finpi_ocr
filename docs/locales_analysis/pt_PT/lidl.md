# Lidl (pt_PT) - Португалия

## Источник
- **Файл:** photo/GOODS/Lidl/photo_2025-12-07 13.26.33.jpeg
- **Ground Truth:** 053_pt_PT_lidl_photo_2025-12-07.json
- **Дата анализа:** 2025-12-26
- **Дата чека:** 08.11.2025, 17:11

## Метаданные чека

| Поле | Значение |
|------|----------|
| Магазин | LIDL & Cia |
| Адрес | R M. Fonte - M. F. Tijolo, Lj37 - Lisboa |
| NIF | 503340855 |
| Capital Social | 498.880 EUR |
| Валюта | EUR |
| Способ оплаты | MULTIBANCO |
| Итого | 3,37 EUR |
| Тип документа | FATURA SIMPLIFICADA |

## Структура чека

```
┌─────────────────────────────────────────┐
│ [Lidl] Vale mesmo a pena.               │
│                                         │
│ LIDL & Cia - LISBOA - R MARIA DA FONTE  │
│ R M. Fonte - M. F. Tijolo, Lj37 - Lisboa│
│ NIF:503340855 C.S. 498.880 EUR          │
│ Rua Pé de Mouro 18,2714-510 Sintra      │
│ C.R.C Sintra N10628 SIRPEE PT000048     │
├─────────────────────────────────────────┤
│ FATURA SIMPLIFICADA                     │
│ Original     Data de Venda: 2025-11-08  │
│ No: FS 018800125/205509                 │
│ NIF...: CONSUMIDOR FINAL                │
├─────────────────────────────────────────┤
│                              EUR        │
│ TRANCA COM NOZ PECA           0,89 A    │
│ PIZZA FIAMBRE E QUEIJO        1,49 A    │
│ FOLHADO DE CARNE MISTO        0,99 A    │
├─────────────────────────────────────────┤
│ Total                          3,37     │
│ MULTIBANCO                     3,37     │
├─────────────────────────────────────────┤
│ Taxa   Base Imp.  Val.Total   Val.IVA   │
│ A 23%    2,74       3,37       0,63     │
├─────────────────────────────────────────┤
│ Registe-se no Lidl Plus e               │
│ poupe nas suas próximas compras         │
│ [Штрих-код]                             │
│ ATCUD: JJY7FV5R-205509                  │
│ [QR-код]                                │
└─────────────────────────────────────────┘
```

## Паттерны

### Товарная строка
```
TRANCA COM NOZ PECA           0,89 A
```
- Формат: название + цена + tax class
- Названия на ПОРТУГАЛЬСКОМ языке
- Uppercase для названий

### Tax Block (IVA)
```
Taxa   Base Imp.  Val.Total   Val.IVA
A 23%    2,74       3,37       0,63
```
- **IVA 23%** - стандартная ставка Португалии
- Другие ставки: 13% (промежуточная), 6% (пониженная)

## Ground Truth

| # | raw_name | total_price | tax_class |
|---|----------|-------------|-----------|
| 1 | TRANCA COM NOZ PECA | 0,89 | A |
| 2 | PIZZA FIAMBRE E QUEIJO | 1,49 | A |
| 3 | FOLHADO DE CARNE MISTO | 0,99 | A |

## Checksum

```
0,89 + 1,49 + 0,99 = 3,37 EUR
Расхождение: 0,00
```

## Отличия от de_DE

| Аспект | de_DE | pt_PT |
|--------|-------|-------|
| НДС | 7%/19% | 23%/13%/6% |
| Ключевое слово | MwSt | IVA |
| Итого | zu zahlen | Total |
| Язык названий | Немецкий | Португальский |
| Документ | Kassenbon | FATURA SIMPLIFICADA |
| Платёжная система | girocard | MULTIBANCO |
| NIF | - | Обязательный |
| ATCUD | - | Обязательный (QR) |

## Ключевые слова (pt_PT)

- **Total** - итого
- **FATURA SIMPLIFICADA** - упрощённый счёт
- **CONSUMIDOR FINAL** - конечный потребитель
- **Data de Venda** - дата продажи
- **Taxa** - ставка налога
- **Base Imp.** - налоговая база
- **Val.Total** - общая сумма
- **Val.IVA** - сумма НДС
- **MULTIBANCO** - платёжная система
- **Registe-se** - зарегистрируйтесь

## Особенности для парсинга

1. **IVA 23%** вместо MwSt 7%/19%
2. **FATURA SIMPLIFICADA** - тип документа
3. **ATCUD** - обязательный код для налоговой
4. **NIF** - налоговый номер магазина
5. **MULTIBANCO** - национальная платёжная система
6. **Португальский язык** для всех названий

