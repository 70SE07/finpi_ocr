#!/usr/bin/env python3
"""
Точка входа для домена Extraction (Pre-OCR + OCR).

Использование:
    # Обработать все изображения из data/input/
    python scripts/extract_raw_ocr.py
    
    # Обработать конкретное изображение
    python scripts/extract_raw_ocr.py path/to/image.jpg
    
    # Принудительный перезапуск (игнорировать кэш)
    python scripts/extract_raw_ocr.py --no-cache

ВАЖНО: Возвращает RawOCRResult из contracts/d1_extraction_dto.py
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import validate_config, INPUT_DIR, OUTPUT_DIR
from src.extraction import ImagePreprocessor, GoogleVisionOCR
from contracts.d1_extraction_dto import RawOCRResult


def process_image(image_path: Path, output_dir: Path, no_cache: bool = False) -> bool:
    """
    Обрабатывает одно изображение через домен Extraction.
    
    Args:
        image_path: Путь к изображению
        output_dir: Директория для сохранения результатов
        no_cache: Игнорировать кэш и перезапустить обработку
        
    Returns:
        True если успешно, False если ошибка
    """
    try:
        # Создаём директорию для результатов
        result_dir = output_dir / image_path.stem
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # Проверяем кэш
        raw_ocr_file = result_dir / "raw_ocr_results.json"
        if not no_cache and raw_ocr_file.exists():
            print(f"  [CACHE] Результаты уже существуют: {raw_ocr_file}")
            return True
        
        print(f"  [1/2] Pre-OCR обработка: {image_path.name}")
        preprocessor = ImagePreprocessor()
        processed_image, metadata = preprocessor.process(image_path)
        
        print(f"  [2/2] OCR через Google Vision")
        ocr = GoogleVisionOCR()
        raw_result = ocr.recognize(processed_image, source_file=image_path.stem)
        
        # Сохраняем сырые результаты (Pydantic -> dict)
        result_dict = raw_result.model_dump()
        with open(raw_ocr_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        print(f"  [SAVED] Сырые результаты сохранены: {raw_ocr_file}")
        print(f"  [INFO]  Слов: {len(raw_result.words)}, символов: {len(raw_result.full_text)}")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Ошибка обработки {image_path.name}: {e}")
        return False


def main():
    """Главная функция запуска домена Extraction."""
    
    print("\n" + "="*60)
    print("  FINPI OCR - Домен Extraction (Pre-OCR + OCR)")
    print("="*60)
    
    # Проверяем конфигурацию
    try:
        validate_config()
        print("\n[OK] Конфигурация проверена")
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    
    print(f"[OK] Input директория: {INPUT_DIR}")
    print(f"[OK] Output директория: {OUTPUT_DIR}")
    
    # Парсинг аргументов
    parser = argparse.ArgumentParser(description="FINPI OCR Extraction Domain")
    parser.add_argument("path", nargs="?", help="Путь к изображению (опционально)")
    parser.add_argument("--no-cache", action="store_true", help="Принудительный перезапуск всех этапов")
    args = parser.parse_args()
    
    # Определяем какие изображения обрабатывать
    if args.path:
        # Обработка одного изображения
        image_path = Path(args.path)
        if not image_path.exists():
            print(f"[ERROR] Файл не найден: {image_path}")
            sys.exit(1)
        
        image_paths = [image_path]
        print(f"\n[PROCESSING] Обработка одного файла: {image_path.name}")
    else:
        # Обработка всех изображений в INPUT_DIR
        if not INPUT_DIR.exists():
            print(f"[ERROR] Input директория не найдена: {INPUT_DIR}")
            sys.exit(1)
        
        image_paths = list(INPUT_DIR.glob("*.jpg")) + list(INPUT_DIR.glob("*.jpeg")) + list(INPUT_DIR.glob("*.png"))
        if not image_paths:
            print(f"[WARNING] В директории {INPUT_DIR} не найдены изображения")
            sys.exit(0)
        
        print(f"\n[PROCESSING] Обработка {len(image_paths)} изображений из {INPUT_DIR}")
    
    # Обрабатываем изображения
    success_count = 0
    total_count = len(image_paths)
    
    for i, image_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{total_count}] {image_path.name}")
        
        if process_image(image_path, OUTPUT_DIR, args.no_cache):
            success_count += 1
    
    # Итоги
    print("\n" + "="*60)
    print(f"  ИТОГИ: {success_count}/{total_count} успешно обработано")
    
    if success_count == total_count:
        print(f"  [SUCCESS] Все изображения обработаны успешно!")
    else:
        print(f"  [WARNING] {total_count - success_count} изображений не обработано")
        sys.exit(1)


if __name__ == "__main__":
    main()
