from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from .store_detector import StoreDetector
from .date_extractor import DateExtractor
from .total_extractor import TotalExtractor
from .address_extractor import AddressExtractor
from .requisites_extractor import RequisitesExtractor

@dataclass
class MetadataResult:
    """Общие метаданные чека."""
    store_name: str
    receipt_date: Optional[str]        # ISO format YYYY-MM-DD
    total_receipt_amount: Optional[float]
    store_brand: Optional[str]
    store_address: Optional[str] = None
    store_phone: Optional[str] = None
    store_vat_id: Optional[str] = None
    confidence_score: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует результат в словарь (чистый вид для ЦКП)."""
        return asdict(self)

class MetadataExtractor:
    """
    Оркестратор для извлечения метаданных.
    Координирует работу специализированных детекторов.
    """
    
    def __init__(
        self, 
        store_detector: Optional[StoreDetector] = None, 
        date_extractor: Optional[DateExtractor] = None,
        total_extractor: Optional[TotalExtractor] = None,
        address_extractor: Optional[AddressExtractor] = None,
        requisites_extractor: Optional[RequisitesExtractor] = None
    ):
        self.store_detector = store_detector or StoreDetector()
        self.date_extractor = date_extractor or DateExtractor()
        self.total_extractor = total_extractor or TotalExtractor()
        self.address_extractor = address_extractor or AddressExtractor()
        self.requisites_extractor = requisites_extractor or RequisitesExtractor()

    def process(self, texts: List[str]) -> MetadataResult:
        """
        Извлекает все доступные метаданные.
        """
        # 1. Сначала ищем вспомогательные данные (адрес, реквизиты)
        address_res = self.address_extractor.extract(texts)
        requisites_res = self.requisites_extractor.extract(texts)

        # 2. Ищем основные данные
        store = self.store_detector.detect(texts, address_res)
        date_res = self.date_extractor.extract(texts)
        total = self.total_extractor.extract(texts)
        
        result = MetadataResult(
            store_name=store.name,
            receipt_date=date_res.date.strftime("%Y-%m-%d") if date_res.date else None,
            total_receipt_amount=total.amount,
            store_brand=store.brand,
            store_address=address_res.address,
            store_phone=requisites_res.phone,
            store_vat_id=requisites_res.vat_id,
            confidence_score={
                "store": store.confidence,
                "receipt_date": date_res.confidence,
                "total_amount": total.confidence,
                "address": address_res.confidence,
                "requisites": requisites_res.confidence
            }
        )
        

        return result
