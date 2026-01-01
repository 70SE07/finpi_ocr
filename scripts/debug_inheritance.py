from src.parsing.locales.config_loader import ConfigLoader

def debug_inheritance():
    print("Загрузка конфигурации для de_DE...")
    try:
        config_loader = ConfigLoader()
        de_config = config_loader.load("de_DE")
        
        # Получаем семантический конфиг (с учетом backward compatibility properties)
        # В LocaleConfig семантика доступна через .semantic
        semantic = de_config.semantic
        
        weight_patterns = semantic.weight_patterns
        tax_patterns = semantic.tax_patterns
        
        print(f"de_DE weight_patterns count: {len(weight_patterns)}")
        print(f"de_DE tax_patterns count: {len(tax_patterns)}")
        
        if weight_patterns:
            print(f"Пример weight_pattern: '{weight_patterns[0]}'")
        else:
            print("WARNING: weight_patterns is EMPTY!")
            
        if tax_patterns:
            print(f"Пример tax_pattern: '{tax_patterns[0]}'")
        else:
            print("WARNING: tax_patterns is EMPTY!")
            
        # Проверка наследования skip_keywords
        skip_keywords = semantic.skip_keywords
        print(f"de_DE skip_keywords count: {len(skip_keywords)}")
        if "gesamter preisvorteil" in skip_keywords:
             print("SUCCESS: 'gesamter preisvorteil' found in skip_keywords (local override)")
        else:
             print("WARNING: 'gesamter preisvorteil' NOT found in skip_keywords")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_inheritance()
