"""
QTY Marker - Маркировка строк с количеством × цена.

Проблема: GPT парсер путается в строках типа "Wasser 0,29 x 30 8,70 B"
- Где цена? 0,29 или 8,70?
- Что такое 30?

Решение: Размечаем явно для GPT:
"[QTY_LINE] Wasser | qty=30 | price=0.29 | TOTAL=8.70 | B"

Теперь парсер точно знает структуру.
"""

import re
from dataclasses import dataclass

from loguru import logger


@dataclass
class QtyMarkerResult:
    """Результат маркировки."""

    original_text: str
    marked_text: str
    lines_marked: int
    marked_lines: list[tuple[str, str]]  # [(original, marked), ...]


class QtyMarker:
    """
    Маркирует строки с паттерном PRICE x QTY TOTAL.

    Паттерн: "Product PRICE x QTY TOTAL [TAX]"
    Пример: "Wasser medium 0,29 x 30 8,70 B"
    Результат: "[QTY_LINE] Wasser medium | qty=30 | price=0.29 | TOTAL=8.70 | B"
    """

    # Pattern: price x qty total [tax indicator]
    # Example: "0,29 x 30 8,70 B" or "1,69 x 2 3,38 A"
    PATTERN = re.compile(r"(\d+[.,]\d{2})\s*x\s*(\d+)\s+(\d+[.,]\d{2})\s*([ABab])?\s*$")

    def __init__(self, enabled: bool = True):
        """
        Args:
            enabled: Включить маркировку (для A/B тестов)
        """
        self.enabled = enabled

    def process(self, text: str) -> QtyMarkerResult:
        """
        Обрабатывает текст и маркирует qty×price строки.

        Args:
            text: OCR текст

        Returns:
            QtyMarkerResult с размеченным текстом и статистикой
        """
        if not self.enabled:
            logger.debug("[QtyMarker] Disabled, skipping")
            return QtyMarkerResult(original_text=text, marked_text=text, lines_marked=0, marked_lines=[])

        result_lines = []
        marked_lines = []

        for line in text.split("\n"):
            match = self.PATTERN.search(line)
            if match:
                price_str = match.group(1).replace(",", ".")
                qty = match.group(2)
                total_str = match.group(3).replace(",", ".")
                tax = match.group(4) or ""

                # Extract product name (everything before the pattern)
                name = line[: match.start()].strip()

                # Reformat line with explicit markers
                marked_line = f"[QTY_LINE] {name} | qty={qty} | price={price_str} | TOTAL={total_str} | {tax}".strip()
                result_lines.append(marked_line)
                marked_lines.append((line, marked_line))

                logger.debug(f"[QtyMarker] '{line}' → '{marked_line}'")
            else:
                result_lines.append(line)

        marked_text = "\n".join(result_lines)

        if marked_lines:
            logger.info(f"[QtyMarker] Размечено {len(marked_lines)} строк")

        return QtyMarkerResult(
            original_text=text, marked_text=marked_text, lines_marked=len(marked_lines), marked_lines=marked_lines
        )


def mark_qty_lines(text: str, enabled: bool = True) -> str:
    """
    Удобная функция для маркировки qty×price строк.

    Args:
        text: OCR текст
        enabled: Включить маркировку

    Returns:
        Размеченный текст
    """
    marker = QtyMarker(enabled=enabled)
    result = marker.process(text)
    return result.marked_text
