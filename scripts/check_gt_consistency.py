"""
Скрипт проверки консистентности Ground Truth файлов.
Проверяет:
- ID в файле соответствует имени файла
- locale соответствует папке
- source_file существует
"""

import json
from pathlib import Path


def main():
    gt_dir = Path("docs/ground_truth")
    issues = []
    stats = {"total": 0, "ok": 0, "issues": 0}

    for locale_dir in sorted(gt_dir.iterdir()):
        if locale_dir.is_dir():
            locale = locale_dir.name
            for gt_file in sorted(locale_dir.glob("*.json")):
                stats["total"] += 1
                file_issues = []
                
                try:
                    with open(gt_file) as f:
                        data = json.load(f)
                    
                    # Извлекаем ID из имени файла
                    filename = gt_file.stem  # например: 008_de_DE_aldi_IMG_1724
                    file_id = filename.split("_")[0]  # 008
                    
                    # Проверяем ID
                    json_id = str(data.get("id", "MISSING")).zfill(3)
                    if json_id != file_id:
                        file_issues.append(f"ID: file={file_id}, json={data.get('id')}")
                    
                    # Проверяем locale
                    json_locale = data.get("locale", "MISSING")
                    if json_locale != locale:
                        file_issues.append(f"LOCALE: folder={locale}, json={json_locale}")
                    
                    # Проверяем source_file существует
                    source = data.get("source_file", "")
                    if source and not Path(source).exists():
                        file_issues.append(f"SOURCE: {source} NOT FOUND")
                    
                    if file_issues:
                        stats["issues"] += 1
                        issues.append((gt_file.name, file_issues))
                    else:
                        stats["ok"] += 1
                        
                except Exception as e:
                    stats["issues"] += 1
                    issues.append((gt_file.name, [f"ERROR: {e}"]))

    print(f"=== Статистика Ground Truth ===")
    print(f"Всего файлов: {stats['total']}")
    print(f"OK: {stats['ok']}")
    print(f"С проблемами: {stats['issues']}")
    print()
    
    if issues:
        print(f"=== Проблемы ({len(issues)} файлов) ===")
        for filename, file_issues in issues:
            print(f"\n{filename}:")
            for issue in file_issues:
                print(f"  - {issue}")


if __name__ == "__main__":
    main()
