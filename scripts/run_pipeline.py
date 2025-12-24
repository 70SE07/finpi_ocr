#!/usr/bin/env python3
"""
Точка входа для запуска OCR пайплайна.

Использование:
    # Обработать все изображения из data/input/
    python scripts/run_pipeline.py
    
    # Обработать конкретное изображение
    python scripts/run_pipeline.py path/to/image.jpg
"""

import sys
import argparse
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import validate_config, INPUT_DIR, OUTPUT_DIR
from src.pipeline import OcrPipeline


def main():
    """Главная функция запуска пайплайна."""
    
    print("\n" + "="*60)
    print("  FINPI OCR - Тренировочный стенд Google Vision")
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
    parser = argparse.ArgumentParser(description="FINPI OCR Pipeline Runner")
    parser.add_argument("path", nargs="?", help="Путь к изображению (опционально)")
    parser.add_argument("--no-cache", action="store_true", help="Принудительный перезапуск всех этапов")
    args = parser.parse_args()
    
    # Инициализируем пайплайн
    pipeline = OcrPipeline()
    use_cache = not args.no_cache
    
    # Определяем что обрабатывать
    if args.path:
        # Конкретный файл
        image_path = Path(args.path)
        if not image_path.exists():
            print(f"\n[ERROR] Файл не найден: {image_path}")
            sys.exit(1)
        
        result = pipeline.process_image(image_path, use_cache=use_cache)
        print(f"\n{'='*60}")
        print("РЕЗУЛЬТАТ:")
        print(f"{'='*60}")
        print(f"\nПолный текст:\n{result.full_text[:500]}...")
    else:
        # Все файлы из input/
        results = pipeline.process_directory(use_cache=use_cache)
        
        if results:
            print(f"\n{'='*60}")
            print("СВОДКА РЕЗУЛЬТАТОВ:")
            print(f"{'='*60}")
            for dto in results:
                print(f"\n{dto.source_file}:")
                print(f"  - Строк: {len(dto.lines)}")
                print(f"  - Символов: {len(dto.full_text)}")
                print(f"  - Уверенность: {dto.ocr_confidence:.2%}")


if __name__ == "__main__":
    main()
