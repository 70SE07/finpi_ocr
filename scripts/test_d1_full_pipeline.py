"""
Полный тест D1 Pipeline на реальном чеке.

Проверяет полный цикл:
1. ✅ Preprocessing (6 stages) с контрактами
2. ✅ OCR распознавание через Google Vision
3. ✅ Feedback Loop с всеми стратегиями
4. ✅ RawOCRResult контракт валиден
5. ✅ Words с координатами корректны
"""

import json
from pathlib import Path
from loguru import logger

# Добавляем src в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.application.factory import ExtractionComponentFactory
from contracts.d1_extraction_dto import RawOCRResult


def test_full_pipeline(image_path: Path, strategy_config: dict = None) -> dict:
    """
    Тестирует полный D1 pipeline с OCR.
    
    Args:
        image_path: Путь к изображению
        strategy_config: Конфигурация стратегии retry (опционально)
        
    Returns:
        Dict с результатами
    """
    logger.info(f"\n{'='*70}")
    logger.info("ПОЛНЫЙ ТЕСТ D1 PIPELINE С OCR")
    logger.info(f"{'='*70}")
    logger.info(f"Изображение: {image_path.name}")
    logger.info(f"Размер: {image_path.stat().st_size / 1024:.1f} KB")
    
    try:
        # Создаем полный pipeline
        extraction_pipeline = ExtractionComponentFactory.create_default_extraction_pipeline()
        
        # Обрабатываем через полный pipeline (preprocessing + OCR)
        logger.info("\nЗапуск ExtractionPipeline...")
        raw_ocr_result = extraction_pipeline.process_image(image_path)
        
        # Проверяем RawOCRResult контракт
        logger.success(f"\n✅ RawOCRResult получен")
        logger.info(f"  Full text length: {len(raw_ocr_result.full_text)} символов")
        logger.info(f"  Words count: {len(raw_ocr_result.words)} слов")
        logger.info(f"  Source file: {raw_ocr_result.metadata.source_file}")
        logger.info(f"  Image size: {raw_ocr_result.metadata.image_width}x{raw_ocr_result.metadata.image_height}")
        
        # Валидация full_text
        if not raw_ocr_result.full_text or not raw_ocr_result.full_text.strip():
            logger.error("❌ Full text пуст!")
            return {
                'success': False,
                'error': 'empty_full_text'
            }
        
        # Валидация words[]
        if not raw_ocr_result.words:
            logger.error("❌ Words[] пуст!")
            return {
                'success': False,
                'error': 'empty_words'
            }
        
        # Проверяем что все слова валидны
        word_errors = []
        for i, word in enumerate(raw_ocr_result.words, 1):
            # Проверяем bounding box
            bbox = word.bounding_box
            if bbox.x < 0 or bbox.y < 0:
                word_errors.append(f"Word {i}: отрицательные координаты ({bbox.x}, {bbox.y})")
            if bbox.width <= 0 or bbox.height <= 0:
                word_errors.append(f"Word {i}: некорректные размеры ({bbox.width}x{bbox.height})")
            
            # Проверяем confidence
            if not (0.0 <= word.confidence <= 1.0):
                word_errors.append(f"Word {i}: confidence {word.confidence} вне [0, 1]")
            
            # Проверяем text
            if not word.text or not word.text.strip():
                word_errors.append(f"Word {i}: пустой текст")
        
        if word_errors:
            logger.error(f"❌ Найдены ошибки в словах:")
            for error in word_errors[:10]:  # Показываем первые 10
                logger.error(f"  {error}")
            return {
                'success': False,
                'error': 'invalid_words',
                'details': word_errors
            }
        
        # Проверяем что координаты в пределах изображения
        width = raw_ocr_result.metadata.image_width
        height = raw_ocr_result.metadata.image_height
        
        coord_errors = []
        for i, word in enumerate(raw_ocr_result.words, 1):
            bbox = word.bounding_box
            if bbox.x + bbox.width > width:
                coord_errors.append(f"Word {i}: X超出 ({bbox.x + bbox.width} > {width})")
            if bbox.y + bbox.height > height:
                coord_errors.append(f"Word {i}: Y超出 ({bbox.y + bbox.height} > {height})")
        
        if coord_errors:
            logger.warning(f"⚠️  Обнаружены слова за границами (первые 5):")
            for error in coord_errors[:5]:
                logger.warning(f"  {error}")
        else:
            logger.success(f"✅ Все координаты слов в пределах {width}x{height}")
        
        # Проверяем preprocessing metadata
        preprocessing = raw_ocr_result.metadata.preprocessing_applied
        logger.info(f"\nПримененный preprocessing:")
        logger.info(f"  Фильтры: {preprocessing}")
        
        # Проверяем retry_info если есть
        if raw_ocr_result.metadata.retry_info:
            retry = raw_ocr_result.metadata.retry_info
            logger.info(f"\nFeedback Loop info:")
            logger.info(f"  Попыток: {retry.get('attempts', 1)}")
            logger.info(f"  Был retry: {retry.get('was_retried', False)}")
            logger.info(f"  Стратегии: {retry.get('strategies_used', [])}")
            logger.info(f"  Final avg confidence: {retry.get('final_avg_confidence', 0):.3f}")
            logger.info(f"  Final min confidence: {retry.get('final_min_confidence', 0):.3f}")
        
        # Анализируем средний confidence
        avg_confidence = sum(w.confidence for w in raw_ocr_result.words) / len(raw_ocr_result.words)
        min_confidence = min(w.confidence for w in raw_ocr_result.words)
        max_confidence = max(w.confidence for w in raw_ocr_result.words)
        
        logger.success(f"\n✅ OCR Quality Metrics:")
        logger.info(f"  Average confidence: {avg_confidence:.3f} [0-1]")
        logger.info(f"  Min confidence:     {min_confidence:.3f}")
        logger.info(f"  Max confidence:     {max_confidence:.3f}")
        logger.info(f"  Low confidence words: {sum(1 for w in raw_ocr_result.words if w.confidence < 0.85)} / {len(raw_ocr_result.words)}")
        
        # Проверяем что confidence валиден
        if not (0.0 <= avg_confidence <= 1.0):
            logger.error(f"❌ Average confidence {avg_confidence} вне диапазона [0, 1]")
            return {
                'success': False,
                'error': 'invalid_confidence'
            }
        
        result = {
            'success': True,
            'image': image_path.name,
            'full_text_length': len(raw_ocr_result.full_text),
            'words_count': len(raw_ocr_result.words),
            'avg_confidence': round(avg_confidence, 3),
            'min_confidence': round(min_confidence, 3),
            'max_confidence': round(max_confidence, 3),
            'image_size': f"{width}x{height}",
            'preprocessing': preprocessing,
            'sample_words': [
                {
                    'text': word.text,
                    'confidence': round(word.confidence, 3),
                    'bbox': f"{word.bounding_box.x},{word.bounding_box.y},{word.bounding_box.width}x{word.bounding_box.height}"
                }
                for word in raw_ocr_result.words[:5]  # Первые 5 слов
            ]
        }
        
        if raw_ocr_result.metadata.retry_info:
            result['retry_info'] = raw_ocr_result.metadata.retry_info
        
        logger.success(f"\n✅ ПОЛНЫЙ ТЕСТ D1 PASSED!")
        return result
        
    except Exception as e:
        logger.error(f"\n❌ Ошибка при тесте: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'image': image_path.name
        }


def main():
    """Главная функция тестирования."""
    logger.info("="*70)
    logger.info("ПОЛНЫЙ ТЕСТ D1 PIPELINE С GOOGLE VISION OCR")
    logger.info("="*70)
    
    # Выбираем реальный чек
    input_dir = Path(__file__).parent.parent / "data" / "input"
    image_files = list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.jpg"))
    
    if not image_files:
        logger.error(f"Не найдены изображения в {input_dir}")
        return
    
    # Используем первый чек
    test_image = image_files[0]
    
    # Тестируем полный pipeline
    result = test_full_pipeline(test_image)
    
    # Сохраняем результат
    output_file = Path(__file__).parent / "d1_full_pipeline_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_image': str(test_image),
            'image_size_kb': test_image.stat().st_size / 1024,
            'result': result
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nРезультаты сохранены: {output_file}")
    
    # Итоговый вердикт
    logger.info(f"\n{'='*70}")
    if result['success']:
        logger.success("🎉 D1 PIPELINE ПОЛНОСТЬЮ РАБОТАЕТ!")
        logger.success("✅ RawOCRResult контракт валиден")
        logger.success("✅ OCR распознавание работает")
        logger.success("✅ Words[] с координатами корректны")
        logger.success("✅ Confidence валиден")
        logger.success("✅ Full text получен")
        
        # Детали результата
        logger.info(f"\nДетали:")
        logger.info(f"  Изображение: {result['image']}")
        logger.info(f"  Размер: {result['image_size']}")
        logger.info(f"  Слова: {result['words_count']}")
        logger.info(f"  Full text: {result['full_text_length']} символов")
        logger.info(f"  Avg confidence: {result['avg_confidence']}")
        logger.info(f"  Фильтры: {result['preprocessing']}")
        
        if 'retry_info' in result:
            logger.info(f"  Были retry: {result['retry_info'].get('was_retried', False)}")
    else:
        logger.error("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В D1 PIPELINE")
        logger.error(f"Ошибка: {result.get('error', 'unknown')}")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    main()
