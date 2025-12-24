
import os
import sys
import cv2
import re
from pathlib import Path
from google.cloud import vision

# Add src to path to use project modules if needed (though we use raw cv2 here mainly)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from pre_ocr import ImageCompressor

# Configuration
INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output/experiments/color_channels")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'config/google_credentials.json'

TARGET_FILES = [
    "IMG_1390.jpeg",  # Lidl, Artifact 1911
    "IMG_1336.jpeg",  # Lidl, Artifact 199.29
    "IMG_1292.jpeg",  # Lidl, Normal (Otsu broke it)
    "IMG_2461.jpeg",  # Thai (Otsu broke it)
]

def run_ocr(image_bytes, client):
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text

def check_artifacts(text, filename):
    results = []
    
    # Check 1911 artifact (IMG_1390)
    if "IMG_1390" in filename:
        if "1911" in text:
            results.append("FAIL: Found '1911'")
        elif re.search(r"1,19\s*A", text):
             results.append("PASS: Found '1,19 A'")
        else:
             results.append("WARN: '1,19' not clearly found")

    # Check 199.29 artifact (IMG_1336)
    if "IMG_1336" in filename:
        if "199.29" in text:
            results.append("FAIL: Found '199.29'")
        elif re.search(r"\s9,29\s*A", text):
             results.append("PASS: Found '9,29 A'")
        else:
             results.append("WARN: '9,29' not clearly found")

    # Check quality for others
    if "IMG_1292" in filename:
        if "Schweinenackenbraten" in text:
            results.append("PASS: Found main item")
        else:
            results.append("FAIL: Main item missing (OCR Broken?)")
            
    if "IMG_2461" in filename:
        # Check for English text preservation
        if "TITLEIST" in text or "Supersports" in text: # Wait, 2461 is 7-Eleven
             if "CP ALL" in text or "7-Eleven" in text:
                 results.append("PASS: Found Header")
             else:
                 results.append("FAIL: Header missing")
        # Check for Thai chars (rough check)
        if any(u'\u0E00' <= c <= u'\u0E7F' for c in text):
             results.append("PASS: Thai chars detected")
        else:
             results.append("FAIL: No Thai chars (OCR Broken?)")

    return "; ".join(results)

def main():
    client = vision.ImageAnnotatorClient()
    compressor = ImageCompressor()

    print(f"{'Filename':<15} | {'Channel':<10} | {'Status':<40} | {'Text Snippet'}")
    print("-" * 100)

    for filename in TARGET_FILES:
        filepath = INPUT_DIR / filename
        if not filepath.exists():
            print(f"File not found: {filename}")
            continue

        # Load and Compress first (Standard Pipeline Step 1)
        original_img = cv2.imread(str(filepath))
        compressed_result = compressor.compress(original_img)
        img = compressed_result.image

        # Channels
        # OpenCV loads as BGR
        b, g, r = cv2.split(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        channels = {
            "Gray (Std)": gray,
            "Blue": b,
            "Green": g,
            "Red": r
        }

        for name, channel_img in channels.items():
            _, encoded = cv2.imencode('.jpg', channel_img)
            text = run_ocr(encoded.tobytes(), client)
            status = check_artifacts(text, filename)
            
            # Find relevant snippet for display
            snippet = ""
            lines = text.split('\n')
            for line in lines:
                if "IMG_1390" in filename and ("1,19" in line or "1911" in line or "Gurken" in line):
                    snippet = line
                    break
                if "IMG_1336" in filename and ("9,29" in line or "199.29" in line or "Puten" in line):
                    snippet = line
                    break
                if "IMG_1292" in filename and "Schweinenacken" in line:
                    snippet = line[:30] + "..."
                    break
                if "IMG_2461" in filename and ("1.45" in line or "Coke" in line):
                     snippet = line
                     break
            if not snippet:
                snippet = lines[0][:30] if lines else "EMPTY"

            print(f"{filename:<15} | {name:<10} | {status:<40} | {snippet}")

if __name__ == "__main__":
    main()
