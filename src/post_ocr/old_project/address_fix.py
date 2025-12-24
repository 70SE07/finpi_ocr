"""
E2: Address Fix - Исправление систематической ошибки OCR в адресах.

ПРОБЛЕМА:
Google Vision систематически распознаёт "51491 Overath" как "514910verath"
- "O" распознаётся как "0"
- Пробел между "51491" и "Overath" пропадает

РЕШЕНИЕ:
Post-OCR исправление через regex замену.

ПАТТЕРН:
514910verath → 51491 Overath
"""

import re
from dataclasses import dataclass

from loguru import logger


@dataclass
class AddressFixResult:
    """Результат исправления адреса."""

    original: str
    fixed: str
    was_fixed: bool
    fixes_count: int


# Паттерны для исправления адресов
ADDRESS_FIXES = [
    # 514910verath → 51491 Overath
    (r"514910verath", "51491 Overath"),
    # Другие варианты
    (r"51491\s*0verath", "51491 Overath"),
    (r"514910\s*verath", "51491 Overath"),
]


def fix_address_in_line(line: str) -> AddressFixResult:
    """
    Исправляет систематические ошибки OCR в адресах.

    Args:
        line: Строка OCR текста

    Returns:
        AddressFixResult с результатом исправления
    """
    original = line
    fixed = line
    fixes_count = 0

    for pattern, replacement in ADDRESS_FIXES:
        if re.search(pattern, fixed, re.IGNORECASE):
            fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
            fixes_count += 1

    was_fixed = fixes_count > 0

    if was_fixed:
        logger.debug(f"E2: Address fix: '{original}' → '{fixed}'")

    return AddressFixResult(original=original, fixed=fixed, was_fixed=was_fixed, fixes_count=fixes_count)


def fix_addresses_in_text(text: str) -> str:
    """
    Исправляет адреса во всём тексте.

    Args:
        text: Полный OCR текст

    Returns:
        Исправленный текст
    """
    lines = text.split("\n")
    result = []

    for line in lines:
        fix_result = fix_address_in_line(line)
        result.append(fix_result.fixed)

    return "\n".join(result)
