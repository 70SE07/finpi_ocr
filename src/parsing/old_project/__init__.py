"""
Устаревший код (old_project).

Эта директория содержит код из старого проекта, который не используется
в текущей архитектуре, но сохранен для справки.

ВАЖНО: Не импортировать этот код в рабочие модули!
"""

from .address_fix import (
    AddressFixResult,
    fix_address_in_line,
    fix_addresses_in_text,
)

__all__ = [
    "AddressFixResult",
    "fix_address_in_line",
    "fix_addresses_in_text",
]
