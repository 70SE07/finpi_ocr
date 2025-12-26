#!/usr/bin/env python3
"""
Точка входа для домена Parsing (обработка сырых результатов OCR).

Использование:
    # Обработать все raw_ocr файлы из data/output/
    python scripts/parse_receipt.py
    
    # Обработать конкретный raw_ocr файл
    python scripts/parse_receipt.py path/to/raw_ocr_results.json
    
    # Обработать директорию с результатами extraction
    python scripts/parse_receipt.py --dir path/to/output/dir
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Optional

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import OUTPUT_DIR
from contracts.raw_ocr_schema import RawOCRResult
from src.parsing.parser.receipt_parser import ReceiptParser


def parse_raw_ocr(raw_ocr_file: Path, output_dir: Path) -> bool:
    """
    Парсит сырые результаты OCR через домен Parsing.
    
    Args:
        raw_ocr_file: Путь к файлу raw_ocr_results.json
        output_dir: Директория для сохранения результатов
        
    Returns:
        True если успешно, False если ошибка
    """
    try:
        # Загружаем сырые результаты
        with open(raw_ocr_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Конвертируем в RawOCRResult
        raw_result = RawOCRResult.from_dict(raw_data)
        
        print(f"  [1/2] Загружено: {len(raw_result.blocks)} блоков, {len(raw_result.full_text)} символов")
        
        # Парсим через ReceiptParser
        print(f"  [2/2] Парсинг через ReceiptParser")
        parser = ReceiptParser()
        result = parser.parse(raw_result.to_dict())
        
        # Сохраняем структурированные результаты
        result_file = output_dir / "parsed_results.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        # Сохраняем детализированный отчёт
        if hasattr(result, 'analysis_trace'):
            trace_file = output_dir / "analysis_trace.json"
            with open(trace_file, 'w', encoding='utf-8') as f:
                json.dump(result.analysis_trace, f, ensure_ascii=False, indent=2)
            print(f"  [SAVED] Детализированный отчёт: {trace_file}")
        
        print(f"  [SAVED] Структурированные результаты: {result_file}")
        print(f"  [INFO]  Извлечено: {len(result.items)} товаров")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Ошибка парсинга {raw_ocr_file.name}: {e}")
        return False


def find_raw_ocr_files(search_dir: Path) -> List[Path]:
    """
    Находит все raw_ocr_results.json файлы в директории.
    
    Args:
        search_dir: Директория для поиска
        
    Returns:
        Список путей к raw_ocr_results.json файлам
    """
    raw_ocr_files = []
    
    # Ищем во всех поддиректориях
    for json_file in search_dir.rglob("raw_ocr_results.json"):
        raw_ocr_files.append(json_file)
    
    return raw_ocr_files


def main():
    """Главная функция запуска домена Parsing."""
    
    print("\n" + "="*60)
    print("  FINPI OCR - Домен Parsing (обработка сырых OCR)")
    print("="*60)
    
    # Парсинг аргументов
    parser = argparse.ArgumentParser(description="FINPI OCR Parsing Domain")
    parser.add_argument("path", nargs="?", help="Путь к raw_ocr_results.json или директории (опционально)")
    parser.add_argument("--dir", help="Директория для поиска raw_ocr файлов")
    args = parser.parse_args()
    
    # Определяем какие файлы обрабатывать
    raw_ocr_files = []
    
    if args.path:
        # Обработка конкретного файла или директории
        input_path = Path(args.path)
        
        if input_path.is_file() and input_path.name == "raw_ocr_results.json":
            # Один файл
            raw_ocr_files = [input_path]
            print(f"\n[PROCESSING] Обработка одного файла: {input_path}")
            
        elif input_path.is_dir():
            # Директория
            raw_ocr_files = find_raw_ocr_files(input_path)
            print(f"\n[PROCESSING] Обработка {len(raw_ocr_files)} файлов из {input_path}")
            
        else:
            print(f"[ERROR] Неверный путь: {input_path}")
            print("  Ожидается: raw_ocr_results.json файл или директория")
            sys.exit(1)
            
    elif args.dir:
        # Директория через --dir
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"[ERROR] Директория не найдена: {dir_path}")
            sys.exit(1)
        
        raw_ocr_files = find_raw_ocr_files(dir_path)
        print(f"\n[PROCESSING] Обработка {len(raw_ocr_files)} файлов из {dir_path}")
        
    else:
        # Обработка всех файлов в OUTPUT_DIR по умолчанию
        if not OUTPUT_DIR.exists():
            print(f"[ERROR] Output директория не найдена: {OUTPUT_DIR}")
            sys.exit(1)
        
        raw_ocr_files = find_raw_ocr_files(OUTPUT_DIR)
        if not raw_ocr_files:
            print(f"[WARNING] В директории {OUTPUT_DIR} не найдены raw_ocr_results.json файлы")
            print(f"  Запустите сначала: python scripts/extract_raw_ocr.py")
            sys.exit(0)
        
        print(f"\n[PROCESSING] Обработка {len(raw_ocr_files)} файлов из {OUTPUT_DIR}")
    
    # Обрабатываем файлы
    success_count = 0
    total_count = len(raw_ocr_files)
    
    for i, raw_ocr_file in enumerate(raw_ocr_files, 1):
        # Определяем output директорию (та же, где лежит raw_ocr файл)
        output_dir = raw_ocr_file.parent
        
        print(f"\n[{i}/{total_count}] {raw_ocr_file.name}")
        
        if parse_raw_ocr(raw_ocr_file, output_dir):
            success_count += 1
    
    # Итоги
    print("\n" + "="*60)
    print(f"  ИТОГИ: {success_count}/{total_count} успешно обработано")
    
    if success_count == total_count:
        print(f"  [SUCCESS] Все файлы обработаны успешно!")
    else:
        print(f"  [WARNING] {total_count - success_count} файлов не обработано")
        sys.exit(1)


if __name__ == "__main__":
    main()
