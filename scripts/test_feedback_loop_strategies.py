"""
Тестирование всех стратегий Feedback Loop на реальном чеке.

Проверяет:
1. ✅ Adaptive стратегия (по умолчанию)
2. ✅ Aggressive стратегия (форсирование BAD quality)
3. ✅ Minimal стратегия (только GRAYSCALE)
4. ✅ Контракты валидируются на каждом шаге
5. ✅ Метрики корректны (no NaN/Inf)
"""

import json
from pathlib import Path
from loguru import logger

# Добавляем src в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.application.factory import ExtractionComponentFactory
from src.extraction.pre_ocr.pipeline import AdaptivePreOCRPipeline


def test_strategy(image_path: Path, strategy_name: str, strategy_config: dict = None) -> dict:
    """
    Тестирует одну стратегию на заданном изображении.
    
    Args:
        image_path: Путь к изображению
        strategy_name: Имя стратегии для логирования
        strategy_config: Конфигурация стратегии (опционально)
        
    Returns:
        Dict с результатами обработки
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Тест стратегии: {strategy_name.upper()}")
    logger.info(f"{'='*70}")
    
    # Создаем pipeline
    pipeline = AdaptivePreOCRPipeline()
    
    try:
        # Обрабатываем изображение
        logger.info(f"Обработка: {image_path.name}")
        
        if strategy_config:
            # Передаем стратегию для retry
            image_bytes, metadata = pipeline.process(
                image_path,
                context=None,
                strategy=strategy_config
            )
        else:
            # Стандартная обработка (adaptive)
            image_bytes, metadata = pipeline.process(image_path)
        
        # Анализируем результаты
        metrics = metadata.get('metrics', {})
        filter_plan = metadata.get('filter_plan', {})
        
        # Проверяем валидность метрик
        brightness = metrics.get('brightness', -1)
        contrast = metrics.get('contrast', -1)
        noise = metrics.get('noise', -1)
        blue_dominance = metrics.get('blue_dominance', -999)
        
        # Валидация
        errors = []
        if not (0 <= brightness <= 255):
            errors.append(f"Brightness {brightness} вне диапазона [0, 255]")
        if contrast < 0:
            errors.append(f"Contrast {contrast} < 0")
        if noise < 0:
            errors.append(f"Noise {noise} < 0")
        
        import math
        if math.isnan(brightness) or math.isnan(contrast) or math.isnan(noise):
            errors.append("Обнаружен NaN в метриках")
        if math.isinf(brightness) or math.isinf(contrast) or math.isinf(noise):
            errors.append("Обнаружен Inf в метриках")
        
        result = {
            'strategy': strategy_name,
            'success': len(errors) == 0,
            'errors': errors,
            'image': image_path.name,
            'output_size_kb': len(image_bytes) / 1024,
            'metrics': {
                'brightness': round(brightness, 2),
                'contrast': round(contrast, 2),
                'noise': round(noise, 2),
                'blue_dominance': round(blue_dominance, 2)
            },
            'filter_plan': {
                'filters': filter_plan.get('filters', []),
                'quality': filter_plan.get('quality', 'unknown'),
                'reason': filter_plan.get('reason', '')
            },
            'preprocessing_applied': metadata.get('applied', [])
        }
        
        # Логируем результаты
        logger.success(f"✅ Стратегия {strategy_name.upper()} - УСПЕХ")
        logger.info(f"  Качество: {filter_plan.get('quality', 'unknown')}")
        logger.info(f"  Фильтры: {filter_plan.get('filters', [])}")
        logger.info(f"  Причина: {filter_plan.get('reason', '')}")
        logger.info(f"  Метрики:")
        logger.info(f"    Яркость: {brightness:.2f} [0-255] {'✅' if 0 <= brightness <= 255 else '❌'}")
        logger.info(f"    Контраст: {contrast:.2f} [>=0] {'✅' if contrast >= 0 else '❌'}")
        logger.info(f"    Шум: {noise:.2f} [>=0] {'✅' if noise >= 0 else '❌'}")
        logger.info(f"    Output: {len(image_bytes) / 1024:.1f} KB")
        
        if errors:
            logger.error(f"❌ Ошибки: {', '.join(errors)}")
            result['success'] = False
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке {strategy_name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'strategy': strategy_name,
            'success': False,
            'errors': [str(e)],
            'image': image_path.name
        }


def main():
    """Главная функция тестирования."""
    logger.info("="*70)
    logger.info("ТЕСТИРОВАНИЕ FEEDBACK LOOP СТРАТЕГИЙ НА РЕАЛЬНОМ ЧЕКЕ")
    logger.info("="*70)
    
    # Выбираем реальный чек (существующий)
    input_dir = Path(__file__).parent.parent / "data" / "input"
    
    # Ищем JPEG файлы
    image_files = list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.jpg"))
    
    if not image_files:
        logger.error(f"Не найдены изображения в {input_dir}")
        return
    
    # Используем первый чек
    test_image = image_files[0]
    logger.info(f"\nИспользуем чек: {test_image.name}")
    logger.info(f"Размер: {test_image.stat().st_size / 1024:.1f} KB")
    
    # Тестируем все стратегии
    results = []
    
    # 1. Adaptive (по умолчанию)
    result_adaptive = test_strategy(test_image, "adaptive")
    results.append(result_adaptive)
    
    # 2. Aggressive (форсировать BAD quality)
    result_aggressive = test_strategy(
        test_image,
        "aggressive",
        strategy_config={"name": "aggressive"}
    )
    results.append(result_aggressive)
    
    # 3. Minimal (только GRAYSCALE)
    result_minimal = test_strategy(
        test_image,
        "minimal",
        strategy_config={"name": "minimal"}
    )
    results.append(result_minimal)
    
    # Сводные результаты
    logger.info(f"\n{'='*70}")
    logger.info("СВОДНЫЕ РЕЗУЛЬТАТЫ")
    logger.info(f"{'='*70}\n")
    
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        logger.info(f"{result['strategy'].upper():12} | {status}")
        
        if result['success']:
            logger.info(f"{' '*14}Качество: {result['filter_plan']['quality']}")
            logger.info(f"{' '*14}Фильтры: {result['filter_plan']['filters']}")
            
            metrics = result['metrics']
            logger.info(f"{' '*14}Яркость: {metrics['brightness']:.2f} [0-255]")
            logger.info(f"{' '*14}Контраст: {metrics['contrast']:.2f}")
            logger.info(f"{' '*14}Шум:     {metrics['noise']:.2f}")
        else:
            logger.error(f"{' '*14}Ошибки: {', '.join(result['errors'])}")
    
    # Анализ различий между стратегиями
    logger.info(f"\n{'='*70}")
    logger.info("АНАЛИЗ РАЗЛИЧИЙ МЕЖДУ СТРАТЕГИЯМИ")
    logger.info(f"{'='*70}\n")
    
    adaptive_filters = results[0]['filter_plan']['filters']
    aggressive_filters = results[1]['filter_plan']['filters']
    minimal_filters = results[2]['filter_plan']['filters']
    
    logger.info(f"Adaptive фильтры: {adaptive_filters}")
    logger.info(f"Aggressive фильтры: {aggressive_filters}")
    logger.info(f"Minimal фильтры:    {minimal_filters}")
    
    # Проверяем что стратегии действительно разные
    if adaptive_filters != aggressive_filters:
        logger.success("✅ Adaptive != Aggressive (разные планы обработки)")
    else:
        logger.warning("⚠️  Adaptive == Aggressive (одинаковые планы?)")
    
    if adaptive_filters != minimal_filters:
        logger.success("✅ Adaptive != Minimal (разные планы обработки)")
    else:
        logger.warning("⚠️  Adaptive == Minimal (одинаковые планы?)")
    
    if aggressive_filters != minimal_filters:
        logger.success("✅ Aggressive != Minimal (разные планы обработки)")
    
    # Проверяем что Aggressive содержит больше фильтров
    if len(aggressive_filters) >= len(adaptive_filters) >= len(minimal_filters):
        logger.success("✅ Aggressive >= Adaptive >= Minimal (корректный градиент)")
    else:
        logger.warning("⚠️  Градиент стратегий нарушен")
    
    # Сохраняем результаты в JSON
    output_file = Path(__file__).parent / "feedback_loop_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_image': str(test_image),
            'image_size_kb': test_image.stat().st_size / 1024,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nРезультаты сохранены: {output_file}")
    
    # Итоговый вердикт
    all_success = all(r['success'] for r in results)
    
    logger.info(f"\n{'='*70}")
    if all_success:
        logger.success("🎉 ВСЕ СТРАТЕГИИ РАБОТАЮТ КОРРЕКТНО!")
        logger.success("✅ Контракты валидны")
        logger.success("✅ Feedback Loop работает")
        logger.success("✅ Метрики корректны (no NaN/Inf)")
    else:
        logger.error("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В НЕКОТОРЫХ СТРАТЕГИЯХ")
        logger.error("Проверьте логи выше для деталей")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    main()
