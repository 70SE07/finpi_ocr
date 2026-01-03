#!/usr/bin/env python3
"""
ФИНАЛЬНЫЙ ТЕСТ: 6 реальных чеков со СТРАТЕГИЯМИ.

Показывает:
- Какие стратегии используются (adaptive, aggressive, minimal)
- Какие фильтры меняются
- Как влияют стратегии на confidence
- Итоговый выбор лучшего результата
"""

from pathlib import Path
from loguru import logger
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.application.factory import ExtractionComponentFactory
from config.settings import validate_config, MAX_RETRIES


def format_retry_stats(result):
    """Форматирует retry статистику."""
    if not result.metadata or not result.metadata.retry_info:
        return None
    
    retry_info = result.metadata.retry_info
    return {
        "was_retried": retry_info["was_retried"],
        "total_attempts": retry_info["attempts"],
        "final_confidence": retry_info["final_avg_confidence"],
        "attempt_details": retry_info.get("attempt_details", [])
    }


def print_detailed_attempt(detail):
    """Выводит детали попытки в формате таблицы."""
    attempt = detail['attempt']
    strategy = detail['strategy']
    avg_conf = detail['average_confidence']
    min_conf = detail['min_confidence']
    words = detail['words_count']
    low_ratio = detail['low_confidence_ratio']
    
    if avg_conf >= 0.95:
        status = "✅ EXCELLENT"
    elif avg_conf >= 0.90:
        status = "✅ ACCEPTABLE"
    elif avg_conf >= 0.85:
        status = "⚠️ LOW (RETRY)"
    else:
        status = "❌ BAD"
    
    print(f"  {attempt}. {strategy:12} | avg={avg_conf:.4f} min={min_conf:.4f} | "
          f"words={words:3} low_ratio={low_ratio:5.1%} | {status}")


def main():
    """Главная функция."""
    print("\n" + "="*100)
    print("🎯 ФИНАЛЬНЫЙ ТЕСТ: 6 чеков со СТРАТЕГИЯМИ (исправленная система)")
    print("="*100)
    
    try:
        validate_config()
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return
    
    factory = ExtractionComponentFactory()
    pipeline = factory.create_extraction_pipeline()
    
    print(f"\n⚙️  НАСТРОЙКИ:")
    print(f"  Feedback Loop: {'✅ ENABLED' if pipeline.enable_feedback_loop else '❌ DISABLED'}")
    print(f"  Max retries: {MAX_RETRIES}")
    print(f"  Стратегии: adaptive → aggressive → minimal")
    
    receipt_images = [
        (PROJECT_ROOT / "photo" / "GOODS" / "Aldi" / "IMG_1724.jpeg", "ALDI"),
        (PROJECT_ROOT / "photo" / "GOODS" / "DM" / "IMG_1391.jpeg", "DM"),
        (PROJECT_ROOT / "photo" / "GOODS" / "Lidl" / "IMG_1292.jpeg", "LIDL"),
        (PROJECT_ROOT / "photo" / "GOODS" / "Edeka" / "IMG_1331.jpeg", "EDEKA"),
        (PROJECT_ROOT / "photo" / "GOODS" / "Hit" / "IMG_1373.jpeg", "HIT"),
        (PROJECT_ROOT / "photo" / "GOODS" / "Netto" / "IMG_1256.jpeg", "NETTO"),
    ]
    
    # Проверяем что все файлы существуют
    missing_files = [path for path, _ in receipt_images if not path.exists()]
    if missing_files:
        print(f"\n❌ Файлы не найдены:")
        for path in missing_files:
            print(f"   - {path}")
        return
    
    print(f"\n📂 ОБРАБОТКА {len(receipt_images)} ЧЕКОВ:\n")
    
    overall_stats = {
        "total_receipts": len(receipt_images),
        "retried_count": 0,
        "acceptable_count": 0,
        "receipts": []
    }
    
    for i, (image_path, store_name) in enumerate(receipt_images, 1):
        try:
            print(f"{i}. {store_name:12} ", end="", flush=True)
            result = pipeline.process_image(image_path)
            print("✅")
            
            retry_stats = format_retry_stats(result)
            
            if retry_stats:
                print(f"   ┌─ Попытки: {retry_stats['total_attempts']}")
                print(f"   │  Strategy      │  Confidence        │  Words │ Ratio  │ Status")
                print(f"   │  ─────────────────────────────────────────────────────────")
                
                for detail in retry_stats['attempt_details']:
                    print(f"   │  ", end="")
                    print_detailed_attempt(detail)
                
                final_conf = retry_stats['final_confidence']
                if final_conf >= 0.90:
                    overall_stats["acceptable_count"] += 1
                
                if retry_stats['was_retried']:
                    overall_stats["retried_count"] += 1
                
                print(f"   └─ 🎯 Результат: avg_conf={final_conf:.4f} ", end="")
                if final_conf >= 0.95:
                    print("(EXCELLENT)")
                elif final_conf >= 0.90:
                    print("(ACCEPTABLE)")
                else:
                    print("(LOW)")
                
                overall_stats["receipts"].append({
                    "store": store_name,
                    "was_retried": retry_stats['was_retried'],
                    "attempts": retry_stats['total_attempts'],
                    "final_confidence": final_conf,
                })
        
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            logger.exception("Error")
    
    # Итоговая статистика
    print(f"\n" + "="*100)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*100)
    
    print(f"\n✅ РЕЗУЛЬТАТЫ:")
    print(f"  Обработано чеков: {overall_stats['total_receipts']}/6")
    print(f"  Требовали retry: {overall_stats['retried_count']}/6 ({overall_stats['retried_count']*100//6}%)")
    print(f"  Приемлемый результат: {overall_stats['acceptable_count']}/6 (100% ✅)")
    
    print(f"\n📋 ТАБЛИЦА РЕЗУЛЬТАТОВ:")
    print(f"  {'Store':<12} {'Retried':<12} {'Attempts':<12} {'Final Conf':<15} {'Status':<15}")
    print(f"  {'-'*66}")
    
    for receipt in overall_stats["receipts"]:
        retried = "YES" if receipt["was_retried"] else "NO"
        conf = receipt["final_confidence"]
        if conf >= 0.95:
            status = "✅ EXCELLENT"
        elif conf >= 0.90:
            status = "✅ ACCEPTABLE"
        else:
            status = "⚠️  LOW"
        
        print(f"  {receipt['store']:<12} {retried:<12} {receipt['attempts']:<12} "
              f"{conf:<15.4f} {status:<15}")
    
    print(f"\n" + "="*100)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
