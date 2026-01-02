import re
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger

@dataclass
class GhostSuffixResult:
    text: str
    was_fixed: bool
    removed_suffix: Optional[str]

class GhostSuffixFixer:
    """
    Удаляет мусорные суффиксы (просвечивание текста) перед ценой.
    
    Вектор: Перенос логики из Legacy H16 Ghost Suffix.
    ЦКП: Чистое название товара без артефактов OCR.
    """
    
    WHITELIST = [
        r"^[XSML]{1,3}$", r"^[xsml]{1,3}$", # Размеры
        r"^\d+[gG]$", r"^\d+[kK][gG]$",      # Вес
        r"^\d+[mM][lL]$", r"^\d+[lL]$", r"^\d+[cC][lL]$", # Объём
        r"^\d+,?\d*%$",                     # Проценты
        r"^[xX]\d+$", r"^\d+[xX]$",         # Количество
        r"^\d+[eE][rR]$", r"^\d+[sS][tT]$", r"^\d+[pP][cC]$",
        r"^[Bb]io$", r"^[Öö]ko$", r"^[Oo]rganic$",
        r"^EM$", r"^M$", r"^QS$", r"^OGT$", r"^HT$", r"^HF$",
        r"^[Aa]$", r"^[Bb]$", r"^[Nn]eu$", r"^[Ww]$"
    ]

    def __init__(self):
        # Паттерн: слово + пробел + суффикс (2-4 симв) + пробел + цена
        self.main_pattern = re.compile(r"(\S+)(\s+)([A-Za-z\d]{2,4})(\s+)(\d+[.,]\d{2})")
        self.whitelist_regexes = [re.compile(p) for p in self.WHITELIST]
        self.garbage_mixed = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{2,4}$")
        self.garbage_digits = re.compile(r"^\d{2,4}$")

    def _is_garbage(self, suffix: str) -> bool:
        # 1. Проверка whitelist
        if any(rx.match(suffix) for rx in self.whitelist_regexes):
            return False
            
        # 2. Смешанный мусор (буквы+цифры)
        if self.garbage_mixed.match(suffix):
            return True
            
        # 3. Только цифры (не год)
        if self.garbage_digits.match(suffix):
            if len(suffix) == 4 and suffix.startswith("20"):
                return False
            return True
            
        return False

    def fix(self, text: str) -> GhostSuffixResult:
        """
        ЦКП: Название без мусорного суффикса.
        """
        if not text:
            return GhostSuffixResult(text=text, was_fixed=False, removed_suffix=None)
            
        removed = None
        
        def replace_callback(match):
            nonlocal removed
            word_before = match.group(1)
            space1 = match.group(2)
            suffix = match.group(3)
            price = match.group(5)
            
            # Если это количество (0,25 x 2) - не трогаем
            if word_before.lower() in ("x", "×"):
                return match.group(0)
                
            if self._is_garbage(suffix):
                removed = suffix
                return f"{word_before}{space1}{price}"
            return match.group(0)

        fixed_text = self.main_pattern.sub(replace_callback, text)
        was_fixed = removed is not None
        
        if was_fixed:
            logger.debug(f"[GhostSuffix] Удален мусор '{removed}' из '{text}'")
            
        return GhostSuffixResult(
            text=fixed_text,
            was_fixed=was_fixed,
            removed_suffix=removed
        )



