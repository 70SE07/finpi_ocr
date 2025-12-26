import sys
from pathlib import Path

# Добавляем корень проекта в пути
sys.path.insert(0, str(Path(__file__).parent.parent))

# TODO: Обновить для использования новых entry points
# from src.pipeline import OcrPipeline
# Временно закомментировано, так как pipeline.py будет удалён

def verify():
    # TODO: Обновить для использования новой архитектуры (Extraction + Parsing домены)
    raise NotImplementedError(
        "Этот скрипт требует обновления для новой архитектуры. "
        "Используйте scripts/run_pipeline.py для запуска полного пайплайна."
    )
    # pipeline = OcrPipeline()
    input_path = Path("data/input")
    
    # Находим все изображения
    images = []
    for ext in [".jpeg", ".jpg", ".png"]:
        images.extend(input_path.glob(f"*{ext}"))
        images.extend(input_path.glob(f"*{ext.upper()}"))
    
    print(f"\nНайдено чеков для проверки: {len(images)}")
    results_summary = []

    for img_path in sorted(images):
        print(f"Обработка: {img_path.name}...")
        try:
            pipeline.process_image(img_path)
            
            # Читаем метаданные
            metadata_file = Path(f"data/output/{img_path.stem}/post_ocr/metadata/{img_path.stem}_metadata.json")
            if metadata_file.exists():
                import json
                with open(metadata_file, "r") as f:
                    data = json.load(f)
                    results_summary.append({
                        "file": img_path.name,
                        "store": data.get("store_name"),
                        "date": data.get("date"),
                        "total": data.get("total_amount")
                    })
        except Exception as e:
            print(f"Ошибка на {img_path.name}: {e}")

    # Печатаем итоговую таблицу
    print(f"\n{'='*80}")
    print(f"{'Файл':<25} | {'Магазин':<15} | {'Дата':<12} | {'Сумма':<10}")
    print(f"{'-'*80}")
    for res in results_summary:
        print(f"{res['file']:<25} | {str(res['store']):<15} | {str(res['date']):<12} | {str(res['total']):<10}")
    print(f"{'='*80}")

if __name__ == "__main__":
    verify()
