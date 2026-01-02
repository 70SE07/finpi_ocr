"""
A/B тест: Влияет ли deskew на качество/скорость OCR?

Вариант A: Оригинал (без обработки)
Вариант B: После deskew (выровненный)

Метрики:
- Время OCR (ms)
- Confidence (если есть)
- Количество распознанных слов
"""

import os
import sys
import time
from pathlib import Path

# Настройка путей
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import cv2
from google.cloud import vision

# Настройка конфига
sys.path.insert(0, str(PROJECT_ROOT.parent))
from config.settings import JPEG_QUALITY

# Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
    PROJECT_ROOT / "config" / "google_credentials.json"
)

from pre_ocr.deskew_cv import DeskewCV


def ocr_image(image_bytes: bytes) -> dict:
    """Выполняет OCR и возвращает метрики."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    start = time.time()
    response = client.document_text_detection(image=image)
    elapsed_ms = (time.time() - start) * 1000
    
    # Подсчёт слов
    word_count = 0
    if response.text_annotations:
        # Первый элемент — полный текст, остальные — слова
        word_count = len(response.text_annotations) - 1
    
    full_text = ""
    if response.full_text_annotation:
        full_text = response.full_text_annotation.text
    
    return {
        "time_ms": elapsed_ms,
        "word_count": word_count,
        "char_count": len(full_text),
        "text_preview": full_text[:100].replace("\n", " ") if full_text else ""
    }


def image_to_bytes(image) -> bytes:
    """Конвертирует cv2 image в bytes."""
    _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buffer.tobytes()


def run_ab_test():
    INPUT_DIR = PROJECT_ROOT / "data" / "input"
    SUPPORTED = {".jpg", ".jpeg", ".png"}
    
    # Получаем список изображений
    images = [f for f in INPUT_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    images.sort()
    
    # Ограничим для теста
    images = images[:5]  # Первые 5 чеков
    
    print("=" * 80)
    print("A/B ТЕСТ: Влияние deskew на OCR")
    print(f"Изображений: {len(images)}")
    print("=" * 80)
    
    processor = DeskewCV()
    results = []
    
    for img_path in images:
        print(f"\n{'='*60}")
        print(f"Файл: {img_path.name}")
        print("=" * 60)
        
        # Загружаем изображение
        image = cv2.imread(str(img_path))
        h, w = image.shape[:2]
        print(f"Размер: {w}x{h}")
        
        # === ВАРИАНТ A: Оригинал ===
        print("\n[A] ОРИГИНАЛ (без deskew):")
        original_bytes = image_to_bytes(image)
        result_a = ocr_image(original_bytes)
        print(f"    Время:  {result_a['time_ms']:.0f} ms")
        print(f"    Слов:   {result_a['word_count']}")
        print(f"    Текст:  {result_a['text_preview'][:50]}...")
        
        # === ВАРИАНТ B: С deskew ===
        print("\n[B] С DESKEW:")
        deskew_result = processor.process(image)
        deskewed_bytes = image_to_bytes(deskew_result.image)
        
        print(f"    Поворот: {deskew_result.rotation_90}°, наклон: {deskew_result.angle:.2f}°")
        
        result_b = ocr_image(deskewed_bytes)
        print(f"    Время:  {result_b['time_ms']:.0f} ms")
        print(f"    Слов:   {result_b['word_count']}")
        print(f"    Текст:  {result_b['text_preview'][:50]}...")
        
        # === СРАВНЕНИЕ ===
        time_diff = result_b['time_ms'] - result_a['time_ms']
        word_diff = result_b['word_count'] - result_a['word_count']
        
        print(f"\n    РАЗНИЦА:")
        print(f"    Время:  {time_diff:+.0f} ms ({'быстрее' if time_diff < 0 else 'медленнее'})")
        print(f"    Слов:   {word_diff:+d}")
        
        results.append({
            "file": img_path.name,
            "rotation": deskew_result.rotation_90,
            "skew": deskew_result.angle,
            "time_a": result_a['time_ms'],
            "time_b": result_b['time_ms'],
            "words_a": result_a['word_count'],
            "words_b": result_b['word_count'],
        })
    
    # === ИТОГО ===
    print("\n" + "=" * 80)
    print("ИТОГО:")
    print("=" * 80)
    
    avg_time_a = sum(r['time_a'] for r in results) / len(results)
    avg_time_b = sum(r['time_b'] for r in results) / len(results)
    avg_words_a = sum(r['words_a'] for r in results) / len(results)
    avg_words_b = sum(r['words_b'] for r in results) / len(results)
    
    print(f"\nВариант A (оригинал):")
    print(f"  Среднее время:  {avg_time_a:.0f} ms")
    print(f"  Среднее слов:   {avg_words_a:.0f}")
    
    print(f"\nВариант B (deskew):")
    print(f"  Среднее время:  {avg_time_b:.0f} ms")
    print(f"  Среднее слов:   {avg_words_b:.0f}")
    
    print(f"\nРАЗНИЦА:")
    print(f"  Время:  {avg_time_b - avg_time_a:+.0f} ms")
    print(f"  Слова:  {avg_words_b - avg_words_a:+.0f}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_ab_test()
