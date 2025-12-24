import re
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger

@dataclass
class RequisitesResult:
    """Результат поиска реквизитов (телефон, налог)."""
    phone: Optional[str] = None
    vat_id: Optional[str] = None
    confidence: float = 0.0

class RequisitesExtractor:
    """
    Экстрактор реквизитов торговой точки.
    Ищет номера телефонов, ИНН, VAT и другие идентификаторы.
    """

    # Шаблоны телефонов (упрощенно)
    PHONE_PATTERN = r"(\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b)"
    
    # Шаблоны VAT / Налогов
    VAT_PATTERNS = [
        r"\bDE\s?\d{9}\b",                # Ust-IdNr (Germany)
        r"\bATU\s?\d{8}\b",               # UID (Austria)
        r"\bCHE\s?\d{9}\b",               # MWST (Switzerland)
        r"ИНН\s*[:\s]*\s*(\d{10,12})\b",  # ИНН (RU)
        r"ІПН\s*[:\s]*\s*(\d{10,12})\b",  # ІПН (UA)
        r"\bNIF\s*[:\s]*\s*(\d{9})\b",    # NIF (PT)
        r"\bNIP\s*[:\s]*\s*(\d{10})\b",   # NIP (PL)
    ]

    def extract(self, texts: List[str]) -> RequisitesResult:
        phone = None
        vat_id = None
        
        header_text = "\n".join(texts[:20]) # Обычно в заголовке
        
        # Поиск телефона
        phone_match = re.search(self.PHONE_PATTERN, header_text)
        if phone_match:
            phone = phone_match.group(0).strip()
            logger.debug(f"[RequisitesExtractor] Найден телефон: {phone}")

        # Поиск VAT
        for pattern in self.VAT_PATTERNS:
            vat_match = re.search(pattern, header_text, re.IGNORECASE)
            if vat_match:
                # Если в шаблоне есть группа (ИНН) — берем её, иначе всю строку
                vat_id = vat_match.group(1) if vat_match.groups() else vat_match.group(0)
                logger.debug(f"[RequisitesExtractor] Найден VAT/ИНН: {vat_id}")
                break

        confidence = 0.0
        if phone: confidence += 0.4
        if vat_id: confidence += 0.5

        return RequisitesResult(phone=phone, vat_id=vat_id, confidence=min(confidence, 1.0))
