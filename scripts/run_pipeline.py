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
import subprocess


def run_extraction(args):
    """Запускает домен Extraction."""
    cmd = [sys.executable, "scripts/extract_raw_ocr.py"]
    if args.path:
        cmd.append(args.path)
    if args.no_cache:
        cmd.append("--no-cache")
    
    print(f"\n[EXTRACTION] Запуск: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_parsing():
    """Запускает домен Parsing."""
    cmd = [sys.executable, "scripts/parse_receipt.py"]
    
    print(f"\n[PARSING] Запуск: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    """Главная функция запуска полного пайплайна."""
    
    print("\n" + "="*60)
    print("  FINPI OCR - Полный пайплайн (Extraction + Parsing)")
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
    parser = argparse.ArgumentParser(description="FINPI OCR Full Pipeline Runner")
    parser.add_argument("path", nargs="?", help="Путь к изображению (опционально)")
    parser.add_argument("--no-cache", action="store_true", help="Принудительный перезапуск всех этапов")
    args = parser.parse_args()
    
    # Запускаем оба домена последовательно
    print("\n" + "="*60)
    print("  ЭТАП 1: Extraction (Pre-OCR + OCR)")
    print("="*60)
    
    if not run_extraction(args):
        print("\n[ERROR] Extraction этап завершился с ошибкой")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("  ЭТАП 2: Parsing (обработка сырых OCR)")
    print("="*60)
    
    if not run_parsing():
        print("\n[ERROR] Parsing этап завершился с ошибкой")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("  [SUCCESS] Полный пайплайн выполнен успешно!")
    print("="*60)


if __name__ == "__main__":
    main()
