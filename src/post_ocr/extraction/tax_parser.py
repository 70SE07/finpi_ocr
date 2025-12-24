import re
from typing import Optional

class TaxParser:
    """Элемент-функция: Извлекает код налога (A, B, % и т.д.)."""
    
    def __init__(self):
        # Обычно налог это одна буква в конце строки после цены или суммы
        self.tax_letter_pattern = re.compile(r'\s([A-G])(?!\w)', re.IGNORECASE)
        self.tax_percent_pattern = re.compile(r'(\d{1,2})\s?%')

    def parse(self, text: str) -> Optional[str]:
        """
        ЦКП: Код налога или None.
        """
        if not text:
            return None
            
        # Ищем буквенный код (A, B...)
        letter_match = self.tax_letter_pattern.search(text)
        if letter_match:
            return letter_match.group(1).upper()
            
        # Ищем процент (на случай строк итогов налога)
        percent_match = self.tax_percent_pattern.search(text)
        if percent_match:
            return f"{percent_match.group(1)}%"
            
        return None
