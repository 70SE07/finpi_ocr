#!/usr/bin/env python3
"""
Тестирование Feedback Loop на реальных чеках.

Обрабатывает 3 реальных чека и показывает:
- Результаты каждой попытки (confidence, стратегия)
- Итоговый результат с retry_info
- Статистику по всем чекам
"""

from pathlib import Path
from loguru import logger
import sys
import json

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.application.factory import ExtractionComponentFactory
from config.settings import (
    validate_config,
    MAX_RETRIES,
    CONFIDENCE_EXCELLENT_THRESHOLD,
    CONFIDENCE_ACCEPTABLE_THRESHOLD,
    CONFIDENCE_RETRY_THRESHOLD,
)


def format_retry_stats(result):
    """Форматирует retry статистику для вывода."""
    if not result.metadata or not result.metadata.retry_info:
        return None
    
    retry_info = result.metadata.retry_info
    
    stats = {
        "was_retried": retry_info["was_retried"],
        "total_attempts": retry_info["attempts"],
        "final_confidence": retry_info["final_avg_confidence"],
        "strategies": retry_info["strategies_used"],
        "attempt_details": []
    }
    
    for detail in retry_info.get("attempt_details", []):
        stats["attempt_details"].append({
            "attempt": detail["attempt"],
            "strategy": detail["strategy"],
            "avg_confidence": detail["average_confidence"],
            "min_confidence": detail["min_confidence"],
            "words": detail["words_count"],
        })
    
    return stats


def print_receipt_analysis(receipt_name, result, retry_stats):
    """Выводит анализ одного чека."""
    print(f"\n{'='*80}")
    print(f"📄 {receipt_name}")
    print(f"{'='*80}")
    
    # Базовая информация
    print(f"\n📊 БАЗОВАЯ ИНФОРМАЦИЯ:")
    print(f"  Words recognized: {len(result.words)}")
    print(f"  Text length: {len(result.full_text)} characters")
    
    if result.metadata:
        print(f"  Image dimensions: {result.metadata.image_width}x{result.metadata.image_height}")
    
    # Retry информация
    if retry_stats:
        print(f"\n🔄 FEEDBACK LOOP АНАЛИЗ:")
        print(f"  Was retried: {'YES' if retry_stats['was_retried'] else 'NO'}")
        print(f"  Total attempts: {retry_stats['total_attempts']}/{MAX_RETRIES + 1}")
        print(f"  Final avg confidence: {retry_stats['final_confidence']:.4f}")
        print(f"  Strategies used: {', '.join(retry_stats['strategies'])}")
        
        # Детали попыток
        print(f"\n  📈 ДЕТАЛИ ПОПЫТОК:")
        for detail in retry_stats["attempt_details"]:
            attempt = detail["attempt"]
            strategy = detail["strategy"]
            avg_conf = detail["avg_confidence"]
            min_conf = detail["min_confidence"]
            words = detail["words"]
            
            # Статус (✅ хорошо, ⚠️ плохо)
            if avg_conf >= CONFIDENCE_ACCEPTABLE_THRESHOLD:
                status = "✅"
                status_text = "ACCEPTABLE"
            elif avg_conf >= CONFIDENCE_RETRY_THRESHOLD:
                status = "⚠️"
                status_text = "LOW (RETRY)"
            else:
                status = "❌"
                status_text = "BAD"
            
            print(f"    {status} Попытка {attempt} ({strategy:12}): "
                  f"avg={avg_conf:.4f}, min={min_conf:.4f}, words={words:3} [{status_text}]")
        
        # Итоговый вывод
        print(f"\n  🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        if retry_stats["final_confidence"] >= CONFIDENCE_ACCEPTABLE_THRESHOLD:
            print(f"     ✅ ПРИЕМЛЕМЫЙ результат")
        else:
            print(f"     ⚠️  НИЗКИЙ confidence (< {CONFIDENCE_ACCEPTABLE_THRESHOLD})")


def main():
    """Главная функция."""
    print("\n" + "="*80)
    print("🚀 ТЕСТИРОВАНИЕ FEEDBACK LOOP НА РЕАЛЬНЫХ ЧЕКАХ")
    print("="*80)
    
    # Проверяем конфигурацию
    try:
        validate_config()
    except Exception as e:
        print(f"\n❌ Ошибка конфигурации: {e}")
        return
    
    # Создаём пайплайн
    factory = ExtractionComponentFactory()
    pipeline = factory.create_extraction_pipeline()
    
    print(f"\n⚙️  НАСТРОЙКИ:")
    print(f"  - Feedback Loop: {'ENABLED ✅' if pipeline.enable_feedback_loop else 'DISABLED'}")
    print(f"  - Max retries: {MAX_RETRIES}")
    print(f"  - Excellent threshold: {CONFIDENCE_EXCELLENT_THRESHOLD}")
    print(f"  - Acceptable threshold: {CONFIDENCE_ACCEPTABLE_THRESHOLD}")
    print(f"  - Retry threshold: {CONFIDENCE_RETRY_THRESHOLD}")
    
    # Список реальных чеков
    receipt_images = [
        (PROJECT_ROOT / "photo" / "GOODS" / "Aldi" / "IMG_1724.jpeg", "ALDI"),
        (PROJECT_ROOT / "photo" / "GOODS" / "DM" / "IMG_1391.jpeg", "DM"),
        (PROJECT_ROOT / "photo" / "GOODS" / "Lidl" / "IMG_1292.jpeg", "LIDL"),
    ]
    
    # Проверяем что все файлы существуют
    missing_files = [path for path, _ in receipt_images if not path.exists()]
    if missing_files:
        print(f"\n❌ Файлы не найдены:")
        for path in missing_files:
            print(f"   - {path}")
        return
    
    print(f"\n📂 ОБРАБОТКА {len(receipt_images)} ЧЕКОВ:")
    
    # Статистика по всем чекам
    overall_stats = {
        "total_receipts": len(receipt_images),
        "total_retries": 0,
        "retried_count": 0,
        "acceptable_count": 0,
        "low_confidence_count": 0,
        "receipts": []
    }
    
    # Обрабатываем каждый чек
    for image_path, store_name in receipt_images:
        try:
            print(f"\n⏳ Обработка {store_name}...", end=" ", flush=True)
            result = pipeline.process_image(image_path)
            print("✅ Готово")
            
            # Собираем статистику
            retry_stats = format_retry_stats(result)
            
            # Выводим анализ
            print_receipt_analysis(store_name, result, retry_stats)
            
            # Обновляем общую статистику
            if retry_stats:
                overall_stats["total_retries"] += retry_stats["total_attempts"]
                if retry_stats["was_retried"]:
                    overall_stats["retried_count"] += 1
                
                if retry_stats["final_confidence"] >= CONFIDENCE_ACCEPTABLE_THRESHOLD:
                    overall_stats["acceptable_count"] += 1
                else:
                    overall_stats["low_confidence_count"] += 1
                
                overall_stats["receipts"].append({
                    "store": store_name,
                    "was_retried": retry_stats["was_retried"],
                    "attempts": retry_stats["total_attempts"],
                    "final_confidence": retry_stats["final_confidence"],
                })
        
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            logger.exception("Error processing receipt")
    
    # Итоговая статистика
    print(f"\n\n" + "="*80)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*80)
    
    print(f"\n✅ Результаты:")
    print(f"  Обработано чеков: {overall_stats['total_receipts']}")
    print(f"  Требовали retry: {overall_stats['retried_count']}/{overall_stats['total_receipts']}")
    print(f"  Приемлемый результат: {overall_stats['acceptable_count']}/{overall_stats['total_receipts']}")
    print(f"  Низкий confidence: {overall_stats['low_confidence_count']}/{overall_stats['total_receipts']}")
    
    if overall_stats['total_retries'] > 0:
        avg_attempts = overall_stats['total_retries'] / overall_stats['total_receipts']
        print(f"\n💰 Стоимость API:")
        print(f"  Всего API запросов: {overall_stats['total_retries']}")
        print(f"  Средне на чек: {avg_attempts:.2f}")
        print(f"  Увеличение стоимости: +{(avg_attempts - 1) * 100:.0f}%")
    
    # Таблица с результатами
    print(f"\n📋 ТАБЛИЦА РЕЗУЛЬТАТОВ:")
    print(f"  {'Store':<10} {'Retried':<10} {'Attempts':<12} {'Final Conf':<12} {'Status':<12}")
    print(f"  {'-'*56}")
    
    for receipt in overall_stats["receipts"]:
        retried = "YES" if receipt["was_retried"] else "NO"
        status = "✅ OK" if receipt["final_confidence"] >= CONFIDENCE_ACCEPTABLE_THRESHOLD else "⚠️  LOW"
        print(f"  {receipt['store']:<10} {retried:<10} {receipt['attempts']:<12} "
              f"{receipt['final_confidence']:<12.4f} {status:<12}")
    
    print(f"\n{'='*80}")
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*80)


if __name__ == "__main__":
    main()
