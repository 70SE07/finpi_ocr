#!/usr/bin/env python3
"""
Демонстрация работы Feedback Loop.

Обрабатывает чеки и показывает:
- Сколько попыток потребовалось
- Какие стратегии использовались
- Метрики confidence для каждой попытки
- Итоговый результат

Использование:
    python scripts/test_feedback_loop.py
"""

from pathlib import Path
from loguru import logger
import sys

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.application.factory import ExtractionComponentFactory
from config.settings import validate_config


def analyze_retry_info(result):
    """Анализирует retry_info из результата."""
    if not result.metadata or not result.metadata.retry_info:
        print("  ❌ Retry info отсутствует")
        return
    
    retry_info = result.metadata.retry_info
    
    print(f"\n  📊 FEEDBACK LOOP СТАТИСТИКА:")
    print(f"  {'='*60}")
    print(f"  Was retried: {'YES' if retry_info['was_retried'] else 'NO'}")
    print(f"  Total attempts: {retry_info['attempts']}")
    print(f"  Final avg confidence: {retry_info['final_avg_confidence']:.4f}")
    print(f"  Final min confidence: {retry_info['final_min_confidence']:.4f}")
    print(f"  Final low conf ratio: {retry_info['final_low_conf_ratio']:.2%}")
    print(f"  Strategies used: {', '.join(retry_info['strategies_used'])}")
    
    if retry_info.get('all_attempts_failed'):
        print(f"  ⚠️  WARNING: Все попытки не достигли порога приемлемости")
    
    print(f"\n  📈 ДЕТАЛИ ПОПЫТОК:")
    print(f"  {'='*60}")
    for detail in retry_info.get('attempt_details', []):
        attempt = detail['attempt']
        strategy = detail['strategy']
        avg_conf = detail['average_confidence']
        min_conf = detail['min_confidence']
        low_ratio = detail['low_confidence_ratio']
        words = detail['words_count']
        
        status = "✅" if avg_conf >= 0.90 else "⚠️" if avg_conf >= 0.85 else "❌"
        
        print(f"  {status} Attempt {attempt} ({strategy}):")
        print(f"     - Avg confidence: {avg_conf:.4f}")
        print(f"     - Min confidence: {min_conf:.4f}")
        print(f"     - Low conf ratio: {low_ratio:.2%}")
        print(f"     - Words count: {words}")


def main():
    """Главная функция."""
    print("🚀 ТЕСТ FEEDBACK LOOP")
    print("="*70)
    
    # Проверяем конфигурацию
    try:
        validate_config()
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return
    
    # Создаём фабрику и пайплайн
    factory = ExtractionComponentFactory()
    pipeline = factory.create_extraction_pipeline()
    
    print(f"\n📋 Настройки:")
    print(f"  - Feedback Loop: {'ENABLED' if pipeline.enable_feedback_loop else 'DISABLED'}")
    
    from config.settings import (
        MAX_RETRIES,
        CONFIDENCE_EXCELLENT_THRESHOLD,
        CONFIDENCE_ACCEPTABLE_THRESHOLD,
        CONFIDENCE_RETRY_THRESHOLD
    )
    
    print(f"  - Max retries: {MAX_RETRIES}")
    print(f"  - Excellent threshold: {CONFIDENCE_EXCELLENT_THRESHOLD}")
    print(f"  - Acceptable threshold: {CONFIDENCE_ACCEPTABLE_THRESHOLD}")
    print(f"  - Retry threshold: {CONFIDENCE_RETRY_THRESHOLD}")
    
    # Ищем тестовые чеки
    test_images = list(Path(PROJECT_ROOT / "data" / "receipts" / "de_DE").glob("*.jpg"))
    
    if not test_images:
        print(f"\n⚠️  Тестовые чеки не найдены в data/receipts/de_DE/")
        print(f"   Попробуем найти в других местах...")
        
        # Альтернативные пути
        alt_paths = [
            PROJECT_ROOT / "data" / "input",
            PROJECT_ROOT / "data",
        ]
        
        for alt_path in alt_paths:
            if alt_path.exists():
                test_images = list(alt_path.glob("**/*.jpg"))[:3]
                if test_images:
                    print(f"   ✅ Найдено {len(test_images)} чеков в {alt_path}")
                    break
    
    if not test_images:
        print(f"\n❌ Не найдено тестовых чеков.")
        print(f"   Положите чеки в data/receipts/de_DE/ или data/input/")
        return
    
    # Ограничиваем количество чеков для демонстрации
    test_images = test_images[:3]
    
    print(f"\n📄 Обработка {len(test_images)} чеков:")
    print("="*70)
    
    for i, image_path in enumerate(test_images, 1):
        print(f"\n{i}. {image_path.name}")
        print(f"   {'-'*60}")
        
        try:
            # Обрабатываем чек
            result = pipeline.process_image(image_path)
            
            # Базовая статистика
            print(f"   ✅ Обработано успешно")
            print(f"   Words: {len(result.words)}")
            print(f"   Text length: {len(result.full_text)} chars")
            
            # Анализируем retry info
            analyze_retry_info(result)
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            logger.exception("Error processing image")
    
    print(f"\n{'='*70}")
    print(f"✅ Тест завершен")


if __name__ == "__main__":
    main()
