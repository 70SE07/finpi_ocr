"""
Тест всех трех стратегий preprocessing:
1. Adaptive (по умолчанию)
2. Aggressive (максимум обработки)
3. Minimal (минимум обработки)

Цель: Проверить что каждая стратегия работает корректно.
"""

from pathlib import Path
from loguru import logger
import sys

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.application.factory import ExtractionComponentFactory


def test_strategy(image_path: Path, strategy_name: str):
    """
    Тестирует указанную стратегию на одном изображении.
    
    Args:
        image_path: Путь к изображению
        strategy_name: Название стратегии ("adaptive", "aggressive", "minimal")
    """
    logger.info(f"{'=' * 80}")
    logger.info(f"Тест стратегии: {strategy_name.upper()}")
    logger.info(f"Изображение: {image_path.name}")
    logger.info(f"{'=' * 80}")
    
    try:
        # Создаем pipeline с Feedback Loop
        # Сначала создаем компоненты
        from config.settings import GOOGLE_APPLICATION_CREDENTIALS
        ocr_provider = ExtractionComponentFactory.create_ocr_provider(GOOGLE_APPLICATION_CREDENTIALS)
        image_preprocessor = ExtractionComponentFactory.create_image_preprocessor()
        
        # Создаем pipeline с Feedback Loop
        pipeline = ExtractionComponentFactory.create_extraction_pipeline(
            ocr_provider=ocr_provider,
            image_preprocessor=image_preprocessor,
        )
        # Включаем Feedback Loop вручную
        pipeline.enable_feedback_loop = True
        
        # Обрабатываем изображение с указанной стратегией
        # Для этого используем метод _process_image_single_attempt напрямую
        result = pipeline._process_image_single_attempt(
            image_path,
            strategy={"name": strategy_name}
        )
        
        # Выводим результаты
        logger.info(f"✅ Результат получен!")
        logger.info(f"   - Слов распознано: {len(result.words)}")
        logger.info(f"   - Длина текста: {len(result.full_text)} символов")
        
        # Метрики confidence
        if result.words:
            confidences = [w.confidence for w in result.words]
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            logger.info(f"   - Средний confidence: {avg_conf:.3f}")
            logger.info(f"   - Минимальный confidence: {min_conf:.3f}")
        
        # Preprocessing info
        if result.metadata and result.metadata.preprocessing_applied:
            logger.info(f"   - Примененные фильтры: {result.metadata.preprocessing_applied}")
        
        # Retry info
        if result.metadata and result.metadata.retry_info:
            retry_info = result.metadata.retry_info
            logger.info(f"   - Были retry: {retry_info.get('was_retried', False)}")
            logger.info(f"   - Попыток: {retry_info.get('attempts', 1)}")
        
        logger.info(f"{'=' * 80}\n")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке: {e}")
        logger.exception(e)
        return None


def main():
    """Основная функция для тестирования всех стратегий."""
    
    # Находим тестовое изображение
    # Используем изображение из data/analysis/pre_ocr_stages/
    test_images_dir = Path("data/analysis/pre_ocr_stages")
    
    # Находим первое .jpg изображение (с именем 0_original.jpg)
    test_images = []
    for item in test_images_dir.iterdir():
        if item.is_dir():
            original_image = item / "0_original.jpg"
            if original_image.exists():
                test_images.append(original_image)
                if len(test_images) >= 1:
                    break
    
    if not test_images:
        logger.error(f"Не найдены тестовые изображения в {test_images_dir}")
        return
    
    test_image = test_images[0]
    logger.info(f"Используем тестовое изображение: {test_image}")
    
    # Тестируем все три стратегии
    strategies = ["adaptive", "aggressive", "minimal"]
    results = {}
    
    for strategy in strategies:
        result = test_strategy(test_image, strategy)
        results[strategy] = result
    
    # Сравниваем результаты
    logger.info(f"\n{'=' * 80}")
    logger.info("СРАВНЕНИЕ СТРАТЕГИЙ")
    logger.info(f"{'=' * 80}")
    
    for strategy, result in results.items():
        if result and result.words:
            confidences = [w.confidence for w in result.words]
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            logger.info(
                f"{strategy.upper():10s}: "
                f"words={len(result.words):3d}, "
                f"avg_conf={avg_conf:.3f}, "
                f"min_conf={min_conf:.3f}, "
                f"filters={result.metadata.preprocessing_applied if result.metadata else 'N/A'}"
            )
    
    logger.info(f"{'=' * 80}")


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    main()
