"""
Скрипт исправления ID в Ground Truth файлах.
ID должен соответствовать номеру в имени файла.
"""

import json
from pathlib import Path


def main():
    gt_dir = Path("docs/ground_truth")
    fixed = 0
    
    for locale_dir in sorted(gt_dir.iterdir()):
        if locale_dir.is_dir():
            for gt_file in sorted(locale_dir.glob("*.json")):
                try:
                    with open(gt_file) as f:
                        data = json.load(f)
                    
                    # Извлекаем ID из имени файла
                    filename = gt_file.stem
                    file_id = filename.split("_")[0]  # "008" -> "008"
                    
                    # Проверяем нужно ли исправлять
                    current_id = str(data.get("id", "")).zfill(3)
                    if current_id != file_id:
                        # Исправляем ID
                        data["id"] = file_id
                        
                        # Сохраняем
                        with open(gt_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        print(f"[FIXED] {gt_file.name}: {current_id} -> {file_id}")
                        fixed += 1
                        
                except Exception as e:
                    print(f"[ERROR] {gt_file.name}: {e}")

    print(f"\n=== Исправлено файлов: {fixed} ===")


if __name__ == "__main__":
    main()
