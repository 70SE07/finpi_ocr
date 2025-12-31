#!/usr/bin/env python3
"""
Сравнительное тестирование: старый ReceiptParser vs новый ParsingPipeline.

Использование:
    python scripts/compare_pipelines.py data/input/IMG_1292.jpeg
    python scripts/compare_pipelines.py --all  # все из data/input/

Выводит:
- Какие метрики совпадают
- Где есть расхождения
- Общую статистику
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import INPUT_DIR, OUTPUT_DIR
from src.extraction.application.factory import ExtractionComponentFactory
from src.parsing.stages.pipeline import ParsingPipeline


def compare_single(image_path: Path) -> Dict[str, Any]:
    """
    Сравнивает результаты старого и нового пайплайнов.
    
    Returns:
        dict: Метрики сравнения
    """
    print(f"\n{'='*70}")
    print(f"  Сравнение: {image_path.name}")
    print(f"{'='*70}")
    
    result = {
        "image": image_path.name,
        "old_pipeline": None,
        "new_pipeline": None,
        "comparison": {},
    }
    
    # ===== D1: Extraction (общий для обоих) =====
    print("\n[D1] Extraction...")
    extractor = ExtractionComponentFactory.create_default_extraction_pipeline()
    raw_ocr = extractor.process_image(image_path)
    print(f"  [OK] Слов: {len(raw_ocr.words)}")
    
    # ===== Старый пайплайн =====
    print("\n[OLD] Старый ReceiptParser...")
    old_result = run_old_pipeline(raw_ocr)
    result["old_pipeline"] = old_result
    
    # ===== Новый пайплайн =====
    print("\n[NEW] Новый ParsingPipeline...")
    new_result = run_new_pipeline(raw_ocr)
    result["new_pipeline"] = new_result
    
    # ===== Сравнение =====
    print("\n" + "-"*70)
    print("  СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("-"*70)
    
    comparison = {}
    
    # Локаль
    old_locale = old_result.get("locale") if old_result else None
    new_locale = new_result.get("locale") if new_result else None
    locale_match = old_locale == new_locale
    comparison["locale_match"] = locale_match
    print(f"\n  Локаль:")
    print(f"    OLD: {old_locale}")
    print(f"    NEW: {new_locale}")
    print(f"    {'MATCH' if locale_match else 'DIFF'}")
    
    # Сумма
    old_total = old_result.get("total_amount") if old_result else None
    new_total = new_result.get("total_amount") if new_result else None
    if old_total is not None and new_total is not None:
        total_diff = abs(old_total - new_total)
        total_match = total_diff < 0.01
    else:
        total_diff = None
        total_match = old_total == new_total
    comparison["total_match"] = total_match
    comparison["total_diff"] = total_diff
    print(f"\n  Сумма:")
    print(f"    OLD: {old_total}")
    print(f"    NEW: {new_total}")
    print(f"    {'MATCH' if total_match else f'DIFF: {total_diff}'}")
    
    # Количество товаров
    old_items = old_result.get("items_count", 0) if old_result else 0
    new_items = new_result.get("items_count", 0) if new_result else 0
    items_match = old_items == new_items
    comparison["items_match"] = items_match
    comparison["items_diff"] = abs(old_items - new_items)
    print(f"\n  Товаров:")
    print(f"    OLD: {old_items}")
    print(f"    NEW: {new_items}")
    print(f"    {'MATCH' if items_match else f'DIFF: {abs(old_items - new_items)}'}")
    
    # Время обработки
    old_time = old_result.get("time_ms", 0) if old_result else 0
    new_time = new_result.get("time_ms", 0) if new_result else 0
    comparison["time_ratio"] = new_time / old_time if old_time > 0 else 0
    print(f"\n  Время (D2):")
    print(f"    OLD: {old_time:.1f}ms")
    print(f"    NEW: {new_time:.1f}ms")
    print(f"    Ratio: {comparison['time_ratio']:.2f}x")
    
    result["comparison"] = comparison
    
    # Итог
    all_match = locale_match and total_match and items_match
    print(f"\n{'='*70}")
    if all_match:
        print(f"  РЕЗУЛЬТАТ: MATCH (все ключевые метрики совпадают)")
    else:
        mismatches = []
        if not locale_match:
            mismatches.append("locale")
        if not total_match:
            mismatches.append("total")
        if not items_match:
            mismatches.append("items_count")
        print(f"  РЕЗУЛЬТАТ: DIFF ({', '.join(mismatches)})")
    print(f"{'='*70}")
    
    return result


def run_old_pipeline(raw_ocr) -> Optional[Dict[str, Any]]:
    """
    Запускает старый ReceiptParser.
    
    Returns:
        dict или None если старый пайплайн недоступен
    """
    import time
    
    try:
        from src.parsing.parser.receipt_parser import ReceiptParser
        
        start = time.time()
        parser = ReceiptParser()
        
        # Старый пайплайн ожидает dict с blocks/full_text
        # Конвертируем RawOCRResult в старый формат
        old_format = {
            "full_text": raw_ocr.full_text,
            "blocks": [],  # Старый формат использовал blocks
            "metadata": raw_ocr.metadata.model_dump() if raw_ocr.metadata else {},
        }
        
        # OcrResultDTO - это dataclass, не dict
        result = parser.parse(old_format, save_output=False)
        time_ms = (time.time() - start) * 1000
        
        # Извлекаем метрики из OcrResultDTO
        # metadata содержит locale, total_amount и т.д.
        metadata = result.metadata if hasattr(result, 'metadata') else {}
        items = result.items if hasattr(result, 'items') else []
        
        return {
            "status": "ok",
            "locale": metadata.get("locale"),
            "total_amount": metadata.get("total_amount"),
            "items_count": len(items),
            "time_ms": time_ms,
        }
        
    except ImportError as e:
        print(f"  [SKIP] Старый пайплайн недоступен: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Ошибка старого пайплайна: {e}")
        return {"status": "error", "error": str(e)}


def run_new_pipeline(raw_ocr) -> Dict[str, Any]:
    """
    Запускает новый ParsingPipeline.
    """
    import time
    
    try:
        start = time.time()
        pipeline = ParsingPipeline()
        result = pipeline.process(raw_ocr)
        time_ms = (time.time() - start) * 1000
        
        return {
            "status": "ok",
            "locale": result.locale.locale_code if result.locale else None,
            "total_amount": result.metadata.receipt_total if result.metadata else None,
            "items_count": len(result.semantic.items) if result.semantic else 0,
            "validation_passed": result.validation.passed if result.validation else False,
            "time_ms": time_ms,
        }
        
    except Exception as e:
        print(f"  [ERROR] Ошибка нового пайплайна: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Сравнение старого и нового пайплайнов")
    parser.add_argument("path", nargs="?", help="Путь к изображению")
    parser.add_argument("--all", action="store_true", help="Обработать все из data/input/")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить количество")
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  FINPI OCR - Сравнение пайплайнов")
    print("  OLD: ReceiptParser (существующий)")
    print("  NEW: ParsingPipeline (D2 по ADR-015)")
    print("="*70)
    
    if args.all:
        images = list(INPUT_DIR.glob("*.jpg")) + list(INPUT_DIR.glob("*.jpeg")) + list(INPUT_DIR.glob("*.png"))
        if not images:
            print(f"[ERROR] Изображения не найдены в {INPUT_DIR}")
            sys.exit(1)
        
        if args.limit:
            images = images[:args.limit]
        
        print(f"\n[INFO] Обработка {len(images)} изображений")
        
        results = []
        for image_path in images:
            result = compare_single(image_path)
            results.append(result)
        
        # Статистика
        print("\n" + "="*70)
        print("  ИТОГОВАЯ СТАТИСТИКА")
        print("="*70)
        
        total = len(results)
        locale_matches = sum(1 for r in results if r["comparison"].get("locale_match", False))
        total_matches = sum(1 for r in results if r["comparison"].get("total_match", False))
        items_matches = sum(1 for r in results if r["comparison"].get("items_match", False))
        
        print(f"\n  Всего: {total}")
        print(f"  Локаль совпадает: {locale_matches}/{total} ({100*locale_matches/total:.0f}%)")
        print(f"  Сумма совпадает: {total_matches}/{total} ({100*total_matches/total:.0f}%)")
        print(f"  Товары совпадают: {items_matches}/{total} ({100*items_matches/total:.0f}%)")
        
        # Сохраняем отчёт
        report_path = OUTPUT_DIR / "comparison_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_images": total,
                "summary": {
                    "locale_matches": locale_matches,
                    "total_matches": total_matches,
                    "items_matches": items_matches,
                },
                "results": results,
            }, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  [SAVED] {report_path}")
        
    elif args.path:
        image_path = Path(args.path)
        if not image_path.exists():
            print(f"[ERROR] Файл не найден: {image_path}")
            sys.exit(1)
        
        compare_single(image_path)
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
