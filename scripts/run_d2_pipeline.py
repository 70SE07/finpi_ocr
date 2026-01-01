#!/usr/bin/env python3
"""
Тестовый скрипт для нового пайплайна D2.

Использование:
    python scripts/run_d2_pipeline.py data/input/IMG_1292.jpeg
    python scripts/run_d2_pipeline.py --all  # обработать все из data/input/

Этот скрипт:
1. Запускает D1 (Extraction) -> RawOCRResult
2. Запускает D2 (Parsing) -> RawReceiptDTO
3. Выводит результаты и метрики
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import INPUT_DIR, OUTPUT_DIR
from src.extraction.application.factory import ExtractionComponentFactory
from src.parsing.stages.pipeline import ParsingPipeline
from src.parsing.locales.config_loader import ConfigLoader


def process_image(image_path: Path, save_output: bool = True) -> dict:
    """
    Обрабатывает изображение через D1 + D2 пайплайны.
    
    Args:
        image_path: Путь к изображению
        save_output: Сохранять ли результаты в файл
        
    Returns:
        dict: Результаты обработки
    """
    print(f"\n{'='*60}")
    print(f"  Обработка: {image_path.name}")
    print(f"{'='*60}")
    
    results = {
        "image": image_path.name,
        "status": "unknown",
        "d1_time_ms": 0,
        "d2_time_ms": 0,
    }
    
    try:
        # ===== D1: Extraction =====
        print("\n[D1] Extraction (Pre-OCR + OCR)...")
        import time
        d1_start = time.time()
        
        extractor = ExtractionComponentFactory.create_default_extraction_pipeline()
        raw_ocr = extractor.process_image(image_path)
        
        d1_time = (time.time() - d1_start) * 1000
        results["d1_time_ms"] = round(d1_time, 1)
        
        print(f"  [OK] Слов извлечено: {len(raw_ocr.words)}")
        print(f"  [OK] Символов в тексте: {len(raw_ocr.full_text)}")
        print(f"  [OK] Время D1: {d1_time:.1f}ms")
        
        # ===== D2: Parsing =====
        print("\n[D2] Parsing (6 этапов по ADR-015)...")
        d2_start = time.time()
        
        # Создаём ConfigLoader для локалей
        config_loader = ConfigLoader()
        parser = ParsingPipeline(config_loader=config_loader)
        result = parser.process(raw_ocr)
        
        d2_time = (time.time() - d2_start) * 1000
        results["d2_time_ms"] = round(d2_time, 1)
        
        # Результаты D2
        dto = result.dto
        validation = result.validation
        
        print(f"\n  [Stage 1: Layout] Строк: {len(result.layout.lines)}")
        print(f"  [Stage 2: Locale] {result.locale.locale_code} (confidence: {result.locale.confidence:.2f})")
        print(f"  [Stage 3: Store] {result.store.store_name or 'Не определён'}")
        print(f"  [Stage 4: Metadata] Дата: {result.metadata.receipt_date}, Сумма: {result.metadata.receipt_total}")
        print(f"  [Stage 5: Semantic] Товаров: {len(result.semantic.items)}, Скидок: {len(result.semantic.discounts)}")
        print(f"  [Stage 6: Validation] {'PASSED' if validation.passed else 'FAILED'} (diff: {validation.difference:.2f})")
        
        print(f"\n  [OK] Время D2: {d2_time:.1f}ms")
        
        # Обновляем результаты
        results["status"] = "success" if validation.passed else "validation_failed"
        results["locale"] = result.locale.locale_code
        results["store"] = result.store.store_name
        results["date"] = str(result.metadata.receipt_date) if result.metadata.receipt_date else None
        results["total_amount"] = result.metadata.receipt_total
        results["items_count"] = len(result.semantic.items)
        results["discounts_count"] = len(result.semantic.discounts)
        results["validation_passed"] = validation.passed
        results["validation_diff"] = validation.difference
        
        # Сохраняем результаты
        if save_output:
            output_dir = OUTPUT_DIR / image_path.stem / "d2_pipeline"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем DTO
            dto_file = output_dir / "raw_receipt_dto.json"
            with open(dto_file, 'w', encoding='utf-8') as f:
                json.dump(dto.model_dump(), f, ensure_ascii=False, indent=2, default=str)
            
            # Сохраняем полный результат
            full_result_file = output_dir / "pipeline_result.json"
            with open(full_result_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n  [SAVED] {dto_file}")
            print(f"  [SAVED] {full_result_file}")
        
        # Итог
        print(f"\n{'='*60}")
        if validation.passed:
            print(f"  РЕЗУЛЬТАТ: OK (checksum passed)")
        else:
            print(f"  РЕЗУЛЬТАТ: CHECKSUM FAILED (diff: {validation.difference:.2f})")
        print(f"  Общее время: {d1_time + d2_time:.1f}ms")
        print(f"{'='*60}")
        
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        print(f"\n  [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    return results


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Тестовый скрипт D2 пайплайна")
    parser.add_argument("path", nargs="?", help="Путь к изображению")
    parser.add_argument("--all", action="store_true", help="Обработать все из data/input/")
    parser.add_argument("--no-save", action="store_true", help="Не сохранять результаты")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  FINPI OCR - Тестирование D2 пайплайна")
    print("="*60)
    
    save_output = not args.no_save
    
    if args.all:
        # Обработать все изображения
        images = list(INPUT_DIR.glob("*.jpg")) + list(INPUT_DIR.glob("*.jpeg")) + list(INPUT_DIR.glob("*.png"))
        if not images:
            print(f"[ERROR] Изображения не найдены в {INPUT_DIR}")
            sys.exit(1)
        
        print(f"\n[INFO] Найдено {len(images)} изображений в {INPUT_DIR}")
        
        results = []
        for image_path in images:
            result = process_image(image_path, save_output)
            results.append(result)
        
        # Статистика
        print("\n" + "="*60)
        print("  ИТОГОВАЯ СТАТИСТИКА")
        print("="*60)
        
        success = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "validation_failed")
        errors = sum(1 for r in results if r["status"] == "error")
        
        print(f"\n  Всего: {len(results)}")
        print(f"  Успешно (checksum passed): {success}")
        print(f"  Checksum failed: {failed}")
        print(f"  Ошибки: {errors}")
        
        if results:
            avg_d1 = sum(r["d1_time_ms"] for r in results) / len(results)
            avg_d2 = sum(r["d2_time_ms"] for r in results) / len(results)
            print(f"\n  Среднее время D1: {avg_d1:.1f}ms")
            print(f"  Среднее время D2: {avg_d2:.1f}ms")
        
    elif args.path:
        # Обработать одно изображение
        image_path = Path(args.path)
        if not image_path.exists():
            print(f"[ERROR] Файл не найден: {image_path}")
            sys.exit(1)
        
        process_image(image_path, save_output)
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
