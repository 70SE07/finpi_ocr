
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(os.getcwd())
sys.path.append(str(PROJECT_ROOT))

from src.extraction.application.factory import ExtractionComponentFactory

def diag():
    image_path = PROJECT_ROOT / "photo/GOODS/Aldi/IMG_1724.jpeg"
    print(f"Running D1 for {image_path.name}...")
    extractor = ExtractionComponentFactory.create_default_extraction_pipeline()
    raw_ocr = extractor.process_image(image_path)
    
    print(f"\nFULL DUMP around Y=840-870:")
    words = sorted(raw_ocr.words, key=lambda w: w.bounding_box.y)
    
    for w in words:
        if 840 <= w.bounding_box.y <= 870:
            print(f"Word: '{w.text:15}' | Y: {w.bounding_box.y:4} | H: {w.bounding_box.height:2} | X: {w.bounding_box.x:4}")

if __name__ == "__main__":
    diag()
