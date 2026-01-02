#!/usr/bin/env python3
"""
Скрипт для анализа качества D1: сравнение OCR результатов с Ground Truth.
Запускает D1 для 12 чеков и выявляет расхождения.
"""

import json
import re
from pathlib import Path
from loguru import logger

# Добавляем корень проекта в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.application.factory import ExtractionComponentFactory


# 12 чеков из 10 локалей для анализа
GROUND_TRUTH_FILES = [
    "docs/ground_truth/007_bg_BG_billa_BG_001.json",
    "docs/ground_truth/006_cs_CZ_hornbach_cz_001.json",
    "docs/ground_truth/001_de_DE_lidl_IMG_1292.json",
    "docs/ground_truth/013_de_DE_dm_IMG_1252.json",
    "docs/ground_truth/009_en_IN_nybc_IMG_2475.json",
    "docs/ground_truth/003_es_ES_consum_IMG_3064.json",
    "docs/ground_truth/010_pl_PL_carrefour_PL_001.json",
    "docs/ground_truth/004_pt_PT_continente_PT_002.json",
    "docs/ground_truth/002_th_TH_7eleven_IMG_2461.json",
    "docs/ground_truth/061_th_TH_7eleven_IMG_2224.json",
    "docs/ground_truth/008_tr_TR_f33enva_TR_001.json",
    "docs/ground_truth/005_uk_UA_dniprom_UA_001.json",
]

OUTPUT_DIR = Path("data/analysis/d1_vs_ground_truth")


def load_ground_truth(gt_path: str) -> dict:
    """Загружает Ground Truth файл."""
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_gt_items(gt_data: dict) -> list[dict]:
    """Извлекает товары из Ground Truth."""
    return gt_data.get("items", [])


def extract_gt_total(gt_data: dict) -> float:
    """Извлекает итоговую сумму из Ground Truth."""
    totals = gt_data.get("totals", {})
    return totals.get("total_amount", 0.0)


def normalize_text(text: str) -> str:
    """Нормализует текст для сравнения."""
    # Убираем лишние пробелы, приводим к lower
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text


def find_item_in_ocr(item_name: str, ocr_text: str) -> bool:
    """Проверяет есть ли товар в OCR тексте."""
    # Нормализуем
    item_norm = normalize_text(item_name)
    ocr_norm = normalize_text(ocr_text)
    
    # Простая проверка - есть ли название в тексте
    # Для более точной проверки нужно учитывать сокращения
    return item_norm in ocr_norm


def analyze_receipt(gt_path: str, pipeline) -> dict:
    """Анализирует один чек: D1 vs Ground Truth."""
    
    gt_data = load_ground_truth(gt_path)
    source_file = gt_data.get("source_file", "")
    locale = gt_data.get("locale", "unknown")
    store = gt_data.get("store", {}).get("brand", "unknown")
    
    gt_name = Path(gt_path).stem
    
    if not source_file or not Path(source_file).exists():
        return {
            "id": gt_name,
            "locale": locale,
            "store": store,
            "status": "SKIP",
            "reason": f"Image not found: {source_file}"
        }
    
    logger.info(f"Processing: {gt_name} ({locale}, {store})")
    
    # Запускаем D1
    try:
        ocr_result = pipeline.process_image(Path(source_file))
        
        if not ocr_result:
            return {
                "id": gt_name,
                "locale": locale,
                "store": store,
                "status": "ERROR",
                "reason": "No OCR result"
            }
        
        full_text = ocr_result.full_text
        words_count = len(ocr_result.words)
        
    except Exception as e:
        return {
            "id": gt_name,
            "locale": locale,
            "store": store,
            "status": "ERROR",
            "reason": str(e)
        }
    
    # Анализируем Ground Truth
    gt_items = extract_gt_items(gt_data)
    gt_total = extract_gt_total(gt_data)
    
    # Проверяем каждый товар
    found_items = []
    missing_items = []
    
    for item in gt_items:
        raw_name = item.get("raw_name", "")
        if find_item_in_ocr(raw_name, full_text):
            found_items.append(raw_name)
        else:
            missing_items.append(raw_name)
    
    # Проверяем итоговую сумму
    total_str = f"{gt_total:.2f}".replace(".", ",")  # Европейский формат
    total_str_dot = f"{gt_total:.2f}"  # Точка
    total_found = total_str in full_text or total_str_dot in full_text
    
    # Результат
    total_items = len(gt_items)
    found_count = len(found_items)
    missing_count = len(missing_items)
    
    accuracy = (found_count / total_items * 100) if total_items > 0 else 0
    
    return {
        "id": gt_name,
        "locale": locale,
        "store": store,
        "status": "OK" if accuracy == 100 and total_found else "ISSUES",
        "words_count": words_count,
        "gt_items_total": total_items,
        "items_found": found_count,
        "items_missing": missing_count,
        "accuracy": round(accuracy, 1),
        "total_amount": gt_total,
        "total_found": total_found,
        "missing_items": missing_items[:5] if missing_items else [],  # Первые 5
        "found_items": found_items[:5] if found_items else [],  # Первые 5 найденных
        "ocr_text_length": len(full_text),
        "ocr_full_text": full_text,  # Полный OCR текст для анализа
    }


def main():
    print("=" * 70)
    print("  D1 vs Ground Truth Analysis")
    print("  Анализ качества OCR для 12 чеков из 10 локалей")
    print("=" * 70)
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Создаём pipeline D1
    logger.info("Initializing D1 pipeline...")
    pipeline = ExtractionComponentFactory.create_default_extraction_pipeline()
    
    results = []
    
    for gt_path in GROUND_TRUTH_FILES:
        result = analyze_receipt(gt_path, pipeline)
        results.append(result)
        
        # Выводим краткий результат
        status = result["status"]
        if status == "OK":
            print(f"  ✅ {result['id']}: {result['accuracy']}% ({result['items_found']}/{result['gt_items_total']} items)")
        elif status == "ISSUES":
            print(f"  ⚠️  {result['id']}: {result['accuracy']}% ({result['items_found']}/{result['gt_items_total']} items)")
            if result.get("missing_items"):
                print(f"      Missing: {result['missing_items'][:3]}...")
        elif status == "SKIP":
            print(f"  ⏭️  {result['id']}: SKIP - {result['reason']}")
        else:
            print(f"  ❌ {result['id']}: ERROR - {result['reason']}")
    
    # Сохраняем результаты
    output_file = OUTPUT_DIR / "analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Итоги
    print()
    print("=" * 70)
    print("  ИТОГИ")
    print("=" * 70)
    
    ok_count = sum(1 for r in results if r["status"] == "OK")
    issues_count = sum(1 for r in results if r["status"] == "ISSUES")
    skip_count = sum(1 for r in results if r["status"] == "SKIP")
    error_count = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"  ✅ OK:     {ok_count}")
    print(f"  ⚠️  Issues: {issues_count}")
    print(f"  ⏭️  Skip:   {skip_count}")
    print(f"  ❌ Error:  {error_count}")
    print()
    
    # Средняя точность
    accuracies = [r["accuracy"] for r in results if "accuracy" in r]
    if accuracies:
        avg_accuracy = sum(accuracies) / len(accuracies)
        print(f"  Средняя точность: {avg_accuracy:.1f}%")
    
    print()
    print(f"  Результаты сохранены: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
