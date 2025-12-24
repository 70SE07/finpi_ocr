
import sys
import json
import re
from pathlib import Path
from types import ModuleType

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- MOCK MISSING DEPENDENCIES (Copy from test_parsing_logic.py) ---
dci = ModuleType("dci")
sys.modules["dci"] = dci

dci_post_ocr = ModuleType("dci.post_ocr")
sys.modules["dci.post_ocr"] = dci_post_ocr
setattr(dci, "post_ocr", dci_post_ocr)

dci_line_grouping = ModuleType("dci.post_ocr.line_grouping")
sys.modules["dci.post_ocr.line_grouping"] = dci_line_grouping
setattr(dci_post_ocr, "line_grouping", dci_line_grouping)

class MockWordData: pass
class MockLineData:
    def __init__(self, text, words=None):
        self.text = text
        self.words = words or []
    def get_text(self):
        return self.text

dci_line_grouping.WordData = MockWordData
dci_line_grouping.LineData = MockLineData
# -------------------------------

from src.post_ocr.old_project.context_line import ContextLine

def verify_file(json_path):
    print(f"### Что в Raw OCR (Сверка):")
    print("")
    print(f"| # | Товар (OCR) | Цена (OCR) | Статус | Отличия / Ошибки |")
    print(f"|---|---|---|---|---|")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    lines = data.get("lines", [])
    
    idx = 0
    parsed_count = 0
    
    for line_obj in lines:
        text = line_obj.get("text", "")
        # Run ContextLine Analysis
        # Note: We pass index 0 as it's not critical for logic
        cl = ContextLine.analyze(MockLineData(text), 0)
        
        parsed_str = ""
        price_str = ""
        status = ""
        error = ""
        
        if cl.is_full_item:
            idx += 1
            parsed_count += 1
            name = text # In real DCI we split name/price, here we just show full text as "Item" implies source line
            price = cl.parsed_value
            tax = cl.tax_code
            
            parsed_str = f"`{text[:30]}...`"
            price_str = f"{price} {tax if tax else ''}"
            status = "✅ OK"
            error = "-"
            
            print(f"| {idx} | {parsed_str} | {price_str} | {status} | {error} |")
        
        # Debug: Show "Partial" matches or failures for specific line types if they look like items?
        # For this verification, user asks for table. We list what we FOUND.
        # If we missed something, it won't be in the table (False Negative).
        
    print("")
    print(f"### Вывод:")
    if parsed_count == 0:
        print("Пайплайн не нашел ни одного товара (FAIL).")
    else:
        print(f"Пайплайн нашел {parsed_count} товаров.")

if __name__ == "__main__":
    target = Path("data/output/IMG_1252_result.json")
    if target.exists():
        verify_file(target)
    else:
        print(f"File not found: {target}")
