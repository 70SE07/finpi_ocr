import re
from typing import Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class CyrillicFixResult:
    text: str
    was_fixed: bool
    replacements: int

class CyrillicFixer:
    """
    Исправляет ошибочно распознанные кириллические символы в латинице.
    
    Вектор: Перенос логики из Legacy H13 Cyrillic Fix.
    ЦКП: Текст без кириллических "двойников" (A, B, C, E и т.д.).
    """
    
    # Таблица замены: кириллица → латиница (визуально похожие)
    MAP = {
        "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K",
        "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X", "У": "Y",
        "Я": "R", "З": "3",
        "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x", "у": "y"
    }
    
    # Локали где кириллица ожидаема (НЕ заменяем)
    # TODO: В будущем передавать локаль в fix()
    CYRILLIC_LOCALES = {"ru", "ua", "bg", "sr", "mk", "by", "kz"}

    def __init__(self):
        self.cyrillic_pattern = re.compile(r"[А-Яа-яЁё]")

    def fix(self, text: str, locale: str = "default") -> CyrillicFixResult:
        """
        ЦКП: Результат исправления.
        """
        if not text or locale in self.CYRILLIC_LOCALES:
            return CyrillicFixResult(text=text, was_fixed=False, replacements=0)
            
        if not self.cyrillic_pattern.search(text):
            return CyrillicFixResult(text=text, was_fixed=False, replacements=0)
            
        fixed_text = text
        replacements = 0
        
        for cyr, lat in self.MAP.items():
            count = fixed_text.count(cyr)
            if count > 0:
                fixed_text = fixed_text.replace(cyr, lat)
                replacements += count
                
        was_fixed = replacements > 0
        if was_fixed:
            logger.debug(f"[CyrillicFixer] Исправлено {replacements} симв. в '{text}'")
            
        return CyrillicFixResult(
            text=fixed_text,
            was_fixed=was_fixed,
            replacements=replacements
        )



