from src.parsing.locales.locale_registry import LocaleRegistry
from src.parsing.extraction.quantity_parser import QuantityParser
from src.parsing.extraction.price_parser import PriceParser
from src.parsing.extraction.line_classifier import LineClassifier
from src.parsing.metadata.store_detector import StoreDetector
from src.parsing.metadata.total_extractor import TotalExtractor

registry = LocaleRegistry()
available = registry.get_available_locales()
print(f"Доступные локали: {available}")

if available:
    config = registry.get_locale_config(available[0])
    
    # QuantityParser
    qp = QuantityParser()
    print(f"QuantityParser создан: {qp.locale_config.code}")
    
    # PriceParser  
    pp = PriceParser()
    print(f"PriceParser создан: {pp.locale_config.code}")
    
    # LineClassifier
    lc = LineClassifier()
    print(f"LineClassifier создан: {lc.locale_config.code}")
    
    # StoreDetector
    sd = StoreDetector()
    plocale_config.code}")
    
    # TotalExtractor
    te = TotalExtractor()
    print(f"TotalExtractor создан: {te.locale_config.code}")
    
    print("\nВсе компоненты успешно используют LocaleRegistry fallback!")
