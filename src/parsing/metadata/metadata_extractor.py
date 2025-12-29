from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from loguru import logger
from .store_detector import StoreDetector
from .date_extractor import DateExtractor
from .total_extractor import TotalExtractor
from .address_extractor import AddressExtractor
from .requisites_extractor import RequisitesExtractor

if TYPE_CHECKING:
    from ..locales.locale_config import LocaleConfig

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
    
    Поддерживает LocaleConfig для масштабирования на 100+ стран.
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

    def process(
        self, 
        texts: List[str],
        locale_config: Optional['LocaleConfig'] = None
    ) -> MetadataResult:
        """
        Извлекает все доступные метаданные.
        
        Args:
            texts: Список строк чека
            locale_config: Конфигурация локали (опционально)
        """
        if locale_config:
            logger.info(f"[MetadataExtractor] Используется локаль: {locale_config.code}")
            # Передаем locale_config в суб-экстракторы, если они поддерживают
            # В будущем: store_detector.set_locale(locale_config) и т.д.
        
        # 1. Сначала ищем вспомогательные данные (адрес, реквизиты)
        address_res = self.address_extractor.extract(texts, locale_config=locale_config)
        requisites_res = self.requisites_extractor.extract(texts)

        # 2. Ищем основные данные
        store = self.store_detector.detect(texts, address_res, locale_config=locale_config)
        date_res = self.date_extractor.extract(texts, locale_config=locale_config)
        total = self.total_extractor.extract(texts, locale_config=locale_config)
        
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



