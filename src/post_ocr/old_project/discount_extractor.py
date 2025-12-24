"""
Системный модуль для извлечения скидок из чеков.

Работает для 100+ локалей без хардкода паттернов под конкретные магазины.

Подход:
1. Ищем строки с отрицательными числами (универсально для всех локалей)
2. Ищем строки с ценой, которая следует после товара (inline discount)
3. Привязываем скидку к предыдущему товару

Типы скидок:
- INLINE: скидка сразу после товара (на той же строке или следующей)
- SUMMARY: общая скидка в конце чека
- ITEM_DISCOUNT: скидка на конкретный товар
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiscountItem:
    """Структура для хранения информации о скидке."""

    name: str  # Название скидки (например "Preisvorteil", "RABATT 20%")
    amount: float  # Сумма скидки (положительное число!)
    discount_type: str  # INLINE, SUMMARY, ITEM_DISCOUNT
    related_item: str = ""  # Связанный товар (если можно определить)
    line_number: int = 0  # Номер строки в тексте
    original_line: str = ""  # Исходная строка


@dataclass
class DiscountExtractionResult:
    """Результат извлечения скидок."""

    discounts: list[DiscountItem] = field(default_factory=list)
    total_discount: float = 0.0  # Общая сумма скидок
    discount_count: int = 0  # Количество скидок


# СИСТЕМНЫЕ паттерны для скидок (работают для 100+ локалей)
# Не привязаны к конкретным словам типа "Preisvorteil" или "Rabatt"
# Ищем отрицательные числа в формате цены

# Паттерн 1: Отрицательное число в формате цены
# Примеры: "-0,30", "-2.00", "- 1,60"
NEGATIVE_PRICE_PATTERN = re.compile(r"^(.+?)\s*-\s*(\d+[.,]\d{2})\s*$")

# Паттерн 2: Слово + отрицательное число (с минусом перед числом)
# Примеры: "Preisvorteil -0,30", "RABATT 20% -1,60"
DISCOUNT_WORD_PATTERN = re.compile(
    r"^([A-Za-zÄÖÜäöüßА-Яа-яÀ-ÿ][A-Za-zÄÖÜäöüßА-Яа-я0-9.,\-&\s%\[\]\']+?)\s+-?\s*(\d+[.,]\d{2})\s*$"
)

# Паттерн 3: Процентная скидка (универсальный)
# Примеры: "RABATT 20%", "20% OFF", "скидка 15%"
PERCENT_DISCOUNT_PATTERN = re.compile(r"(\d{1,3})\s*%", re.IGNORECASE)

# Ключевые слова для определения скидок (мультиязычные)
# Используем для классификации, не для поиска
DISCOUNT_KEYWORDS = {
    # Немецкий
    "preisvorteil",
    "rabatt",
    "ersparnis",
    "aktion",
    "angebot",
    # Английский
    "discount",
    "off",
    "save",
    "savings",
    "deal",
    # Русский
    "скидка",
    "экономия",
    "акция",
    "выгода",
    # Французский
    "remise",
    "reduction",
    "promo",
    # Испанский
    "descuento",
    "oferta",
    "ahorro",
    # Итальянский
    "sconto",
    "offerta",
    "risparmio",
    # Польский
    "rabat",
    "znizka",
    "promocja",
    # Чешский/Словацкий
    "sleva",
    "akce",
    "zlava",
}

# Ключевые слова для ИТОГО скидок (НЕ являются отдельными скидками)
# Эти строки показывают общую сумму скидок, а не отдельную скидку
DISCOUNT_TOTAL_KEYWORDS = {
    # Немецкий
    "gesamter preisvorteil",
    "gesamte ersparnis",
    "ihre ersparnis",
    # Английский
    "total savings",
    "total discount",
    "you saved",
    "your savings",
    # Русский
    "итого скидка",
    "всего сэкономлено",
    "ваша экономия",
    # Французский
    "total remise",
    "economie totale",
    # Испанский
    "descuento total",
    "ahorro total",
    # Итальянский
    "sconto totale",
    "risparmio totale",
}


def is_discount_line(line: str) -> bool:
    """
    Определяет, является ли строка скидкой.

    СИСТЕМНЫЙ подход:
    1. Строка содержит отрицательное число ИЛИ
    2. Строка содержит ключевое слово скидки + число
       (после Line Grouping минус может теряться!)
    3. Строка НЕ является итогом скидок
    """
    line_lower = line.lower().strip()

    # Проверка 0: Это итого скидок? (НЕ является отдельной скидкой)
    if any(kw in line_lower for kw in DISCOUNT_TOTAL_KEYWORDS):
        return False

    # Проверка 1: Есть отрицательное число?
    has_negative = "-" in line and re.search(r"-\s*\d+[.,]\d{2}", line)

    # Проверка 2: Есть ключевое слово скидки + число?
    # ВАЖНО: После Line Grouping минус может теряться (OCR bug)
    # Например: "Preisvorteil 0,30" вместо "Preisvorteil -0,30"
    has_keyword = any(kw in line_lower for kw in DISCOUNT_KEYWORDS)
    has_price = re.search(r"\d+[.,]\d{2}", line) is not None

    # Скидка если:
    # 1. Есть отрицательное число, ИЛИ
    # 2. Есть ключевое слово скидки + число (даже без минуса)
    return has_negative or (has_keyword and has_price)


def extract_discount_amount(line: str) -> float:
    """
    Извлекает сумму скидки из строки.

    Возвращает положительное число (скидка всегда уменьшает сумму).

    ВАЖНО: После Line Grouping минус может теряться!
    Например: "Preisvorteil 0,30" вместо "Preisvorteil -0,30"
    Поэтому для строк с ключевыми словами берём число без минуса.
    """
    # Попытка 1: Ищем отрицательное число (с минусом)
    match = re.search(r"-\s*(\d+[.,]\d{2})", line)
    if match:
        amount_str = match.group(1).replace(",", ".")
        try:
            return abs(float(amount_str))
        except ValueError:
            pass

    # Попытка 2: Ключевое слово скидки + число (минус мог потеряться)
    line_lower = line.lower()
    if any(kw in line_lower for kw in DISCOUNT_KEYWORDS):
        # Ищем последнее число в строке (сумма скидки обычно в конце)
        matches = re.findall(r"(\d+[.,]\d{2})", line)
        if matches:
            # Берём последнее число (сумма скидки)
            amount_str = matches[-1].replace(",", ".")
            try:
                return abs(float(amount_str))
            except ValueError:
                pass

    return 0.0


def extract_discounts(text: str) -> DiscountExtractionResult:
    """
    Извлекает все скидки из текста чека.

    СИСТЕМНЫЙ подход:
    1. Проходим по всем строкам
    2. Определяем, является ли строка скидкой
    3. Извлекаем сумму
    4. Привязываем к предыдущему товару

    Args:
        text: Текст чека (после OCR)

    Returns:
        DiscountExtractionResult с детализацией скидок
    """
    result = DiscountExtractionResult()
    lines = text.split("\n")
    prev_product_name = ""  # Название товара (строка БЕЗ цены)
    prev_line = ""  # Предыдущая строка (для названия скидки)

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Проверяем, является ли строка скидкой
        if is_discount_line(line):
            amount = extract_discount_amount(line)

            if amount > 0:
                # Определяем название скидки
                name = re.sub(r"-?\s*\d+[.,]\d{2}\s*$", "", line).strip()
                name = re.sub(r"^-\s*", "", name).strip()

                # Если название пустое, берём из предыдущей строки
                if not name and prev_line:
                    prev_lower = prev_line.lower()
                    if any(kw in prev_lower for kw in DISCOUNT_KEYWORDS):
                        name = prev_line.strip()

                if not name:
                    name = "Discount"

                # Определяем связанный товар
                # Используем prev_product_name (название товара БЕЗ цены)
                if prev_product_name:
                    discount_type = "ITEM_DISCOUNT"
                    related_item = prev_product_name
                else:
                    discount_type = "INLINE"
                    related_item = ""

                discount = DiscountItem(
                    name=name[:50],
                    amount=amount,
                    discount_type=discount_type,
                    related_item=related_item[:50] if related_item else "",
                    line_number=i + 1,
                    original_line=line[:80],
                )
                result.discounts.append(discount)
                result.total_discount += amount
                result.discount_count += 1
        else:
            # Определяем тип строки
            has_price = re.search(r"\d+[.,]\d{2}\s*[ABab]?\s*$", line)
            is_discount_keyword = any(kw in line.lower() for kw in DISCOUNT_KEYWORDS)

            if has_price and not is_discount_keyword:
                # Строка с ценой — это либо "название цена" либо просто "цена"
                # Извлекаем название из строки (до цены)
                item_name = re.sub(r"\s*\d+[.,]\d{2}.*$", "", line).strip()
                item_name = re.sub(r"\s*\d+[.,]\d+\s*x\s*\d+\s*$", "", item_name).strip()

                if item_name:
                    # Строка содержит и название и цену: "Hähn.Keulen Diavolo 3,99 x 2 7,98 A"
                    prev_product_name = item_name
                elif prev_line and not any(kw in prev_line.lower() for kw in DISCOUNT_KEYWORDS):
                    # Строка только с ценой: "2,69 A" — название на предыдущей строке
                    # Проверяем что prev_line похожа на название (не цена, не скидка)
                    if not re.search(r"^\d+[.,]\d{2}", prev_line):
                        prev_product_name = prev_line
            elif not has_price and not is_discount_keyword:
                # Строка без цены и без ключевых слов скидки — возможно название товара
                # Но не обновляем prev_product_name сразу, ждём пока увидим цену
                pass

        # Сохраняем текущую строку
        prev_line = line

    return result


def count_price_lines(text: str) -> int:
    """
    Подсчитывает количество строк с ценами в тексте.

    СИСТЕМНЫЙ подход:
    - Ищем строки с числом в формате X.XX или X,XX
    - Исключаем строки со скидками (отрицательные числа)
    - Исключаем строки с итогами (summe, total, zu zahlen, etc.)

    Args:
        text: Текст чека

    Returns:
        Количество строк с ценами (ожидаемое количество товаров)
    """
    count = 0

    # Ключевые слова для исключения (итого, налоги, служебные строки)
    skip_keywords = {
        "summe",
        "gesamt",
        "total",
        "subtotal",
        "netto",
        "brutto",
        "mwst",
        "vat",
        "tax",
        "iva",
        "tva",
        "dph",
        "zu zahlen",
        "to pay",
        "a payer",
        "a pagar",
        "karte",
        "card",
        "bar",
        "cash",
        "preisvorteil",
        "rabatt",
        "discount",
        "скидка",
        "pfand",
        "deposit",
        "залог",
        "lade dir",
        "download",
        "app",
    }

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        line_lower = line.lower()

        # Пропускаем служебные строки
        if any(kw in line_lower for kw in skip_keywords):
            continue

        # Пропускаем строки с отрицательными числами (скидки)
        if "-" in line and re.search(r"-\s*\d+[.,]\d{2}", line):
            continue

        # Ищем цену в формате X.XX или X,XX
        # Должна быть в конце строки или перед буквой A/B (налоговый код)
        if re.search(r"\d+[.,]\d{2}\s*[ABab]?\s*$", line):
            count += 1
        # Также считаем QTY_LINE строки
        elif "[QTY_LINE]" in line:
            count += 1

    return count


if __name__ == "__main__":
    # Тест на примере IMG_1292.jpeg
    test_text = """
Schweinenackenbraten 10,85 A
Preisvorteil -0,30
Fairtrade Rosen 2,99 x 4 11,96 A
Gurken 0,95 x 2 1,90 A
Preisvorteile -0,40
Zaziki 1,79 A
Preisvorteil -0,14
Bull'sEyeFeink Honey 3,99 A
Preisvorteil -2,00
Hahn Keulen Diavolo 3,99 x 2 7,98 A
RABATT 20% -1,60
zu zahlen 143,37
Gesamter Preisvorteil 4,44
"""

    print("=== Тест извлечения скидок ===\n")

    result = extract_discounts(test_text)

    print(f"Найдено скидок: {result.discount_count}")
    print(f"Общая сумма скидок: {result.total_discount:.2f}\n")

    for d in result.discounts:
        print(f"  - {d.name}: {d.amount:.2f} ({d.discount_type})")
        if d.related_item:
            print(f"    Связан с: {d.related_item}")

    print("\n=== Тест подсчёта строк с ценами ===\n")

    price_lines = count_price_lines(test_text)
    print(f"Строк с ценами: {price_lines}")

    # Проверка: 4.44 = 0.30 + 0.40 + 0.14 + 2.00 + 1.60
    expected_total = 0.30 + 0.40 + 0.14 + 2.00 + 1.60
    print(f"\nОжидаемая сумма скидок: {expected_total:.2f}")
    print(f"Извлечённая сумма: {result.total_discount:.2f}")
    print(f"Совпадение: {'✓' if abs(expected_total - result.total_discount) < 0.01 else '✗'}")
