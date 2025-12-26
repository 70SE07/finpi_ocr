"""
Экстракторы метаданных для домена Parsing.

Содержит компоненты для извлечения магазина, даты, суммы, адреса, реквизитов.
"""

from .store_detector import StoreDetector, StoreResult
from .address_extractor import AddressExtractor, AddressResult
from .date_extractor import DateExtractor, DateResult
from .total_extractor import TotalExtractor, TotalResult
from .metadata_extractor import MetadataExtractor
from .requisites_extractor import RequisitesExtractor

__all__ = [
    "StoreDetector", "StoreResult",
    "AddressExtractor", "AddressResult",
    "DateExtractor", "DateResult",
    "TotalExtractor", "TotalResult",
    "MetadataExtractor",
    "RequisitesExtractor",
]
