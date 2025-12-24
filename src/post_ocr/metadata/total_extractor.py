import re
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger

from config.settings import TOTAL_AMOUNT_MIN, TOTAL_AMOUNT_MAX

@dataclass
class TotalResult:
    """Результат извлечения итоговой суммы."""
    amount: Optional[float]
    text: str
    confidence: float = 0.0

class TotalExtractor:
    """
    Извлекает итоговую сумму чека.
    Ищет ключевые слова и берет ближайшее к ним число.
    """
    
    # Ключевые слова для суммы (мультиязычные)
    KEYWORDS = [
        r"summe", r"total", r"gesamt", r"итого", r"сумма", 
        r"betrag", r"zu zahlen", r"a pagar", r"razem", 
        r"tutar", r"tva", r"brutto", r"netto", r"suma",
        r"cyma", r"cuma", r"cymma", r"сума", r"сумма",
        r"оплата", r"pagar", r"fatura", r"liq"
    ]
    
    # Высокоприоритетные слова (точно ИТОГ)
    PRIORITY_KEYWORDS = [r"summe", r"total", r"итого", r"сумма", r"cyma", r"сума", r"razem"]

    def extract(self, texts: List[str]) -> TotalResult:
        """
        Ищет итоговую сумму в тексте.
        """
        # 1. Ищем строки с ключевыми словами (идем СНИЗУ ВВЕРХ)
        # Так как ИТОГ обычно в самом низу, и мы хотим избежать Netto/Brutto из середины.
        candidates = []
        for i in range(len(texts) - 1, -1, -1):
            text = texts[i]
            lower_text = text.lower()
            
            if any(re.search(rf"\b{kw}\b", lower_text) for kw in self.KEYWORDS):
                logger.trace(f"[TotalExtractor] Найдено ключевое слово в строке: '{text}'")
                search_area = texts[i:i+6]
                for area_text in search_area:
                    # Регекс: сначала ищем 2 знака, потом 3
                    patterns = [
                        r"(\b\d{1,3}(?:\s?\d{3})*(?:[.,]\d{2})\b)",
                        r"(\b\d{1,3}(?:\s?\d{3})*(?:[.,]\d{2,3})?\b)"
                    ]
                    
                    for p_idx, p in enumerate(patterns):
                        matches = list(re.finditer(p, area_text))
                        for m in matches:
                            prefix = area_text[max(0, m.start()-10):m.start()]
                            if "#" in prefix: continue
                            if "%" in area_text: continue
                            
                            val_str = m.group(1).replace(" ", "")
                            try:
                                if "," in val_str and "." in val_str:
                                    val = float(val_str.replace(".", "").replace(",", "."))
                                elif "," in val_str:
                                    val = float(val_str.replace(",", "."))
                                else:
                                    val = float(val_str)
                                
                                if TOTAL_AMOUNT_MIN < val < TOTAL_AMOUNT_MAX:
                                    is_priority = any(re.search(rf"\b{kw}\b", lower_text) for kw in self.PRIORITY_KEYWORDS)
                                    # Ранг: 0 - высший (2 знака + приоритет-слово), 5 - низший
                                    rank = p_idx * 2  # 0 или 2
                                    if not is_priority: rank += 1 # 1 или 3
                                    
                                    logger.debug(f"[TotalExtractor] Кандидат: {val} (rank={rank}, priority={is_priority}, text='{area_text}')")
                                    candidates.append({
                                        'val': val,
                                        'rank': rank,
                                        'text': area_text,
                                        'confidence': 0.95 if is_priority else 0.8
                                    })
                            except ValueError: continue
        
        if candidates:
            # Сортируем по рангу (сначала 2 знака, потом приоритетные слова)
            candidates.sort(key=lambda x: x['rank'])
            best = candidates[0]
            logger.info(f"[TotalExtractor] Выбрана сумма: {best['val']} (rank={best['rank']})")
            return TotalResult(amount=best['val'], text=best['text'], confidence=best['confidence'])
                        
        # 2. Fallback: поиск по всему тексту максимального значения
        all_text = "\n".join(texts)
        # Ищем все суммы, исключая даты
        amounts = []
        for m in re.finditer(r"(\d+[.,]\d{2})", all_text):
            tail = all_text[m.end():m.end()+5]
            if not re.match(r"^[./-](20\d{2}|\d{2})", tail):
                try:
                    amounts.append(float(m.group(1).replace(",", ".")))
                except ValueError: continue
        
        if amounts:
            # Исключаем аномально большие значения (например, номера карт)
            amounts = [a for a in amounts if a < TOTAL_AMOUNT_MAX]
            if amounts:
                best_val = max(amounts)
                logger.info(f"[TotalExtractor] Использован Fallback (max): {best_val}")
                return TotalResult(amount=best_val, text="Fallback max", confidence=0.4)

        logger.warning("[TotalExtractor] Сумма не найдена")
        return TotalResult(amount=None, text="", confidence=0.0)
