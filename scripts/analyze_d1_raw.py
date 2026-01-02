"""
Скрипт для анализа raw OCR результата D1.
Прогоняет grayscale изображения через OCR и выводит результат.
"""

from pathlib import Path
from src.extraction.infrastructure.ocr.google_vision_ocr import GoogleVisionOCR


def main():
    ocr = GoogleVisionOCR()
    
    receipts = [
        ("ЧЕК 1: LIDL (DE)", "data/analysis/pre_ocr_stages/001_de_DE_lidl_IMG_1292/2_grayscale.jpg"),
        ("ЧЕК 2: 7-ELEVEN (TH)", "data/analysis/pre_ocr_stages/002_th_TH_7eleven_IMG_2461/2_grayscale.jpg"),
        ("ЧЕК 3: CONSUM (ES)", "data/analysis/pre_ocr_stages/003_es_ES_consum_IMG_3064/2_grayscale.jpg"),
    ]
    
    for name, path in receipts:
        print(f"=== {name} ===")
        with open(path, "rb") as f:
            img_bytes = f.read()
        result = ocr.recognize(img_bytes, Path(path).stem)
        print(result.full_text)
        print()
        print("=" * 60)
        print()


if __name__ == "__main__":
    main()
