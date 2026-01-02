#!/usr/bin/env python3
"""
Скрипт анализа файлов raw_ocr_results.json.

Проверяет соответствие контракту D1 (RawOCRResult):
- Должен быть ключ 'words', НЕ 'blocks'
- metadata должен быть заполнен

Использование:
    # Анализ без изменений
    python scripts/analyze_raw_ocr_files.py
    
    # Предпросмотр удаления файлов с blocks
    python scripts/analyze_raw_ocr_files.py --dry-run
    
    # Удаление файлов с blocks
    python scripts/analyze_raw_ocr_files.py --delete
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import OUTPUT_DIR


def analyze_file(file_path: Path) -> Dict[str, Any]:
    """
    Анализирует один файл raw_ocr_results.json.
    
    Returns:
        dict с результатами:
        - has_words: bool
        - has_blocks: bool
        - has_metadata: bool
        - metadata_empty: bool
        - valid: bool (соответствует контракту)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        has_words = 'words' in data
        has_blocks = 'blocks' in data
        has_metadata = 'metadata' in data
        metadata_empty = not data.get('metadata') or data.get('metadata') == {}
        
        # Валидный = есть words, нет blocks, metadata не пустой
        valid = has_words and not has_blocks and not metadata_empty
        
        return {
            'file': str(file_path),
            'has_words': has_words,
            'has_blocks': has_blocks,
            'has_metadata': has_metadata,
            'metadata_empty': metadata_empty,
            'valid': valid,
            'error': None
        }
        
    except json.JSONDecodeError as e:
        return {
            'file': str(file_path),
            'has_words': False,
            'has_blocks': False,
            'has_metadata': False,
            'metadata_empty': True,
            'valid': False,
            'error': f"JSON decode error: {e}"
        }
    except Exception as e:
        return {
            'file': str(file_path),
            'has_words': False,
            'has_blocks': False,
            'has_metadata': False,
            'metadata_empty': True,
            'valid': False,
            'error': str(e)
        }


def find_raw_ocr_files(search_dir: Path) -> List[Path]:
    """Находит все raw_ocr_results.json в директории."""
    return list(search_dir.rglob("raw_ocr_results.json"))


def print_report(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Выводит отчёт об анализе."""
    total = len(results)
    with_words = sum(1 for r in results if r['has_words'])
    with_blocks = sum(1 for r in results if r['has_blocks'])
    valid = sum(1 for r in results if r['valid'])
    with_errors = sum(1 for r in results if r['error'])
    metadata_empty = sum(1 for r in results if r['metadata_empty'])
    
    print("\n" + "="*70)
    print("  АНАЛИЗ raw_ocr_results.json ФАЙЛОВ")
    print("="*70)
    
    print(f"\n  Всего файлов: {total}")
    print(f"  С полем 'words': {with_words}")
    print(f"  С полем 'blocks': {with_blocks}")
    print(f"  С пустым metadata: {metadata_empty}")
    print(f"  Валидных (соответствуют контракту): {valid}")
    print(f"  С ошибками чтения: {with_errors}")
    
    # Детализация по файлам с blocks
    if with_blocks > 0:
        print("\n" + "-"*70)
        print("  ФАЙЛЫ С 'blocks' (нарушают контракт):")
        print("-"*70)
        for r in results:
            if r['has_blocks']:
                print(f"    {r['file']}")
    
    # Файлы с ошибками
    if with_errors > 0:
        print("\n" + "-"*70)
        print("  ФАЙЛЫ С ОШИБКАМИ:")
        print("-"*70)
        for r in results:
            if r['error']:
                print(f"    {r['file']}: {r['error']}")
    
    print("\n" + "="*70)
    
    return {
        'total': total,
        'with_words': with_words,
        'with_blocks': with_blocks,
        'valid': valid,
        'with_errors': with_errors
    }


def delete_invalid_files(results: List[Dict[str, Any]], dry_run: bool = True) -> int:
    """
    Удаляет файлы с 'blocks' (не соответствуют контракту).
    
    Args:
        results: Результаты анализа
        dry_run: Если True, только показывает что будет удалено
        
    Returns:
        Количество удалённых файлов
    """
    files_to_delete = [r for r in results if r['has_blocks']]
    
    if not files_to_delete:
        print("\n[INFO] Нет файлов для удаления.")
        return 0
    
    print("\n" + "-"*70)
    if dry_run:
        print("  РЕЖИМ DRY-RUN: файлы НЕ будут удалены")
    else:
        print("  УДАЛЕНИЕ файлов с 'blocks'")
    print("-"*70)
    
    deleted = 0
    for r in files_to_delete:
        file_path = Path(r['file'])
        if dry_run:
            print(f"    [DRY-RUN] Будет удалён: {file_path}")
        else:
            try:
                file_path.unlink()
                print(f"    [DELETED] {file_path}")
                deleted += 1
            except Exception as e:
                print(f"    [ERROR] Не удалось удалить {file_path}: {e}")
    
    print(f"\n  Итого: {deleted if not dry_run else 0} файлов удалено")
    if dry_run:
        print(f"  (в режиме dry-run было бы удалено: {len(files_to_delete)})")
    
    return deleted


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Анализ файлов raw_ocr_results.json на соответствие контракту D1"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Удалить файлы с 'blocks' (не соответствуют контракту)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет удалено, но не удалять"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Директория для поиска (по умолчанию: {OUTPUT_DIR})"
    )
    args = parser.parse_args()
    
    # Находим файлы
    search_dir = args.dir
    if not search_dir.exists():
        print(f"[ERROR] Директория не найдена: {search_dir}")
        sys.exit(1)
    
    print(f"\n[INFO] Поиск в: {search_dir}")
    files = find_raw_ocr_files(search_dir)
    
    if not files:
        print("[INFO] Файлы raw_ocr_results.json не найдены.")
        sys.exit(0)
    
    print(f"[INFO] Найдено файлов: {len(files)}")
    
    # Анализируем
    results = [analyze_file(f) for f in files]
    
    # Выводим отчёт
    stats = print_report(results)
    
    # Удаление если запрошено
    if args.delete or args.dry_run:
        delete_invalid_files(results, dry_run=args.dry_run)
    
    # Код возврата: 0 если все файлы валидны
    if stats['with_blocks'] > 0:
        print("\n[WARNING] Есть файлы с 'blocks'. Используйте --delete для удаления.")
        sys.exit(1)
    else:
        print("\n[OK] Все файлы соответствуют контракту (или файлов нет).")
        sys.exit(0)


if __name__ == "__main__":
    main()
