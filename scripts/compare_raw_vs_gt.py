#!/usr/bin/env python3
"""
Сравнение RAW OCR результата с Ground Truth.
Проверяет что OCR ничего не потерял.
"""

import json
import sys
from pathlib import Path

def compare(raw_path: str, gt_path: str):
    # Загружаем данные
    with open(raw_path, 'r') as f:
        raw = json.load(f)

    with open(gt_path, 'r') as f:
        gt = json.load(f)

    full_text = raw['full_text'].lower()

    print("="*70)
    print("  СРАВНЕНИЕ RAW OCR vs GROUND TRUTH")
    print("="*70)

    # 1. Магазин и адрес
    print("\n[1] МАГАЗИН И АДРЕС")
    checks = [
        ("Lidl", "lidl" in full_text),
        ("Steinhauser", "steinhauser" in full_text),
        ("Auel 1", "auel 1" in full_text),
        ("51491", "51491" in full_text),
        ("Vilkerath", "vilkerath" in full_text),
    ]
    for name, found in checks:
        status = "OK" if found else "MISSING"
        print(f"  [{status}] {name}")

    # 2. Метаданные
    print("\n[2] МЕТАДАННЫЕ")
    checks = [
        ("Дата 31.07.2025", "31.07.2025" in full_text),
        ("Время 12:41", "12:41" in full_text),
        ("Итого 143,37", "143,37" in full_text or "143.37" in full_text),
        ("Экономия 4,44", "4,44" in full_text),
        ("Kartenzahlung", "kartenzahlung" in full_text),
        ("girocard", "girocard" in full_text),
    ]
    for name, found in checks:
        status = "OK" if found else "MISSING"
        print(f"  [{status}] {name}")

    # 3. Налоговый блок
    print("\n[3] НАЛОГОВЫЙ БЛОК")
    checks = [
        ("A 7%", "7 %" in full_text or "a 7 %" in full_text or "7%" in full_text),
        ("B 19%", "19 %" in full_text or "b 19 %" in full_text or "19%" in full_text),
        ("Netto A: 104,90", "104,90" in full_text),
        ("Netto B: 26,16", "26,16" in full_text),
        ("MWST A: 7,34", "7,34" in full_text),
        ("MWST B: 4,97", "4,97" in full_text),
        ("Brutto A: 112,24", "112,24" in full_text),
        ("Brutto B: 31,13", "31,13" in full_text),
    ]
    for name, found in checks:
        status = "OK" if found else "MISSING"
        print(f"  [{status}] {name}")

    # 4. Товары
    print("\n[4] ТОВАРЫ (31 позиций)")
    found_count = 0
    missing = []

    for item in gt['items']:
        name = item['raw_name'].lower()
        price = item['total_price']
        
        # Проверяем название (с учетом умлаутов)
        name_variants = [
            name,
            name.replace("ä", "a").replace("ö", "o").replace("ü", "u"),
        ]
        name_found = any(v in full_text for v in name_variants)
        
        # Проверяем цену (с запятой как в немецком)
        price_str = f"{abs(price):.2f}".replace(".", ",")
        price_found = price_str in full_text
        
        if name_found and price_found:
            found_count += 1
        else:
            missing.append({
                'name': item['raw_name'],
                'price': price,
                'name_found': name_found,
                'price_found': price_found,
                'price_str': price_str
            })

    print(f"  Найдено: {found_count}/31 товаров")

    if missing:
        print(f"\n  Не найдено или частично ({len(missing)}):")
        for m in missing:
            status_name = "OK" if m['name_found'] else "MISSING"
            status_price = "OK" if m['price_found'] else "MISSING"
            print(f"    - {m['name']}: name=[{status_name}], price=[{status_price}] ({m['price_str']})")

    # 5. Итоговая статистика
    print("\n" + "="*70)
    print("  ИТОГ")
    print("="*70)
    print(f"  Слов в raw: {len(raw['words'])}")
    print(f"  Символов в full_text: {len(raw['full_text'])}")
    print(f"  Товаров найдено: {found_count}/31")

    # Критические данные
    critical_checks = [
        ("Итого 143,37", "143,37" in full_text),
        ("Магазин Lidl", "lidl" in full_text),
        ("Дата 31.07", "31.07" in full_text),
    ]
    
    all_critical = all(c[1] for c in critical_checks)
    
    print("\n  Критические данные:")
    for name, found in critical_checks:
        status = "OK" if found else "MISSING"
        print(f"    [{status}] {name}")
    
    if all_critical and found_count >= 28:
        print("\n  [SUCCESS] OCR захватил все критические данные")
        print(f"  [SUCCESS] {found_count}/31 товаров найдено (>90%)")
    else:
        print("\n  [WARNING] Есть потери данных")


if __name__ == "__main__":
    raw_path = "data/output/IMG_1292/raw_ocr_results.json"
    gt_path = "docs/ground_truth/001_de_DE_lidl_IMG_1292.json"
    compare(raw_path, gt_path)
