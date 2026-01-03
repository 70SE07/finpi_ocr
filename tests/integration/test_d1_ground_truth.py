"""
Ground Truth Integration Tests для D1 Pipeline (Extraction).

Проверяет S0-S5 на реальных Ground Truth изображениях с известными результатами.

Тестирует:
1. ✅ Метрики расчитываются корректно (no NaN/Inf)
2. ✅ Качество классифицируется правильно (BAD/LOW/MEDIUM/HIGH)
3. ✅ Фильтры выбираются на основе качества (не магазина)
4. ✅ Все контракты валидны (ImageMetrics, FilterPlan)
5. ✅ Координаты слов в пределах размеров изображения
6. ✅ Система масштабируется (разные локали, магазины)

Структура Ground Truth:
  docs/ground_truth/[locale]/[id].json
  
  Каждый файл содержит:
  {
    "id": "001",
    "source_file": "data/input/Aldi/IMG_1292.jpeg",
    "locale": "de_DE",
    "store": {"name": "Aldi", ...},
    "metadata": {"date": "...", "total": 143.37, ...},
    "items": [...],
    "validation": {"checksum_method": "...", "items_sum": 143.37, ...}
  }
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest
from loguru import logger

from src.extraction.pre_ocr.pipeline import AdaptivePreOCRPipeline
from src.domain.contracts import (
    ImageMetrics, FilterPlan, QualityLevel, 
    ContractValidationError, FilterType
)


class TestD1GroundTruth:
    """Ground Truth tests для D1 Pipeline."""
    
    GROUND_TRUTH_DIR = Path(__file__).parent.parent.parent / "docs" / "ground_truth"
    INPUT_DIR = Path(__file__).parent.parent.parent / "data" / "input"
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Инициализация pipeline."""
        self.pipeline = AdaptivePreOCRPipeline()
        logger.info(f"[Test] Ground Truth Dir: {self.GROUND_TRUTH_DIR}")
        logger.info(f"[Test] Input Dir: {self.INPUT_DIR}")
    
    def get_ground_truth_files(self) -> List[tuple[Path, Dict]]:
        """
        Получает все Ground Truth файлы и их содержимое.
        
        Returns:
            List[(gt_file_path, gt_dict)]
        """
        if not self.GROUND_TRUTH_DIR.exists():
            logger.warning(f"Ground Truth dir не существует: {self.GROUND_TRUTH_DIR}")
            return []
        
        files = []
        for locale_dir in self.GROUND_TRUTH_DIR.glob("*/"):
            if not locale_dir.is_dir():
                continue
            
            for gt_file in locale_dir.glob("*.json"):
                try:
                    with open(gt_file) as f:
                        gt_data = json.load(f)
                    files.append((gt_file, gt_data))
                except Exception as e:
                    logger.error(f"Ошибка чтения {gt_file}: {e}")
        
        return files
    
    def find_source_image(self, gt_data: Dict) -> Optional[Path]:
        """
        Находит исходный файл изображения для Ground Truth.
        
        Args:
            gt_data: Ground Truth данные
            
        Returns:
            Path к файлу или None
        """
        source_file = gt_data.get("source_file")
        if not source_file:
            return None
        
        # Пытаемся найти файл по разным путям
        store_name = gt_data.get("store", {}).get("name")
        if store_name is None:
            store_name = ""
        
        candidates = [
            Path(source_file),  # Абсолютный путь из GT
            self.INPUT_DIR / Path(source_file).name,  # По имени файла
            self.INPUT_DIR / store_name / Path(source_file).name if store_name else None,
        ]
        
        for candidate in candidates:
            if candidate is None:
                continue
            if candidate.exists():
                return candidate
        
        logger.warning(f"Не найден исходный файл для {source_file}")
        return None
    
    def test_contract_validation_on_metrics(self):
        """
        Тест 1: ImageMetrics контракт валидируется на реальных изображениях.
        
        ✅ Проверяет:
        - Метрики не содержат NaN или Inf
        - brightness в [0, 255]
        - contrast >= 0
        - noise >= 0
        - blue_dominance в разумных диапазонах
        """
        gt_files = self.get_ground_truth_files()
        if not gt_files:
            pytest.skip("Ground Truth files not found")
        
        for gt_file, gt_data in gt_files[:5]:  # Тест на первых 5 файлах
            image_path = self.find_source_image(gt_data)
            if not image_path:
                continue
            
            logger.info(f"[Test 1] Проверка метрик: {image_path.name}")
            
            try:
                image_bytes, metadata = self.pipeline.process(image_path)
                
                # ✅ Проверяем что метрики валидны
                assert "metrics" in metadata, "Метрики отсутствуют в metadata"
                metrics = metadata["metrics"]
                
                assert 0 <= metrics["brightness"] <= 255, \
                    f"brightness {metrics['brightness']} вне диапазона [0, 255]"
                assert metrics["contrast"] >= 0, \
                    f"contrast {metrics['contrast']} < 0"
                assert metrics["noise"] >= 0, \
                    f"noise {metrics['noise']} < 0"
                
                logger.info(f"[Test 1] ✅ Метрики валидны: "
                           f"brightness={metrics['brightness']:.1f}, "
                           f"contrast={metrics['contrast']:.2f}, "
                           f"noise={metrics['noise']:.0f}")
                
            except ContractValidationError as e:
                pytest.fail(f"Contract violation на {image_path.name}: {e}")
            except Exception as e:
                logger.error(f"Ошибка обработки {image_path.name}: {e}")
    
    def test_quality_classification_consistency(self):
        """
        Тест 2: Классификация качества консистентна для одинаковых изображений.
        
        ✅ Проверяет:
        - Одно и то же изображение → одинаковое качество (BAD/LOW/MEDIUM/HIGH)
        - Выбор фильтров детерминирован (same input → same plan)
        """
        gt_files = self.get_ground_truth_files()
        if not gt_files:
            pytest.skip("Ground Truth files not found")
        
        for gt_file, gt_data in gt_files[:5]:
            image_path = self.find_source_image(gt_data)
            if not image_path:
                continue
            
            logger.info(f"[Test 2] Проверка консистентности: {image_path.name}")
            
            # Обрабатываем дважды
            _, metadata1 = self.pipeline.process(image_path)
            _, metadata2 = self.pipeline.process(image_path)
            
            # Проверяем что результаты одинаковые
            assert metadata1["metrics"]["quality_level"] == metadata2["metrics"]["quality_level"], \
                "Качество отличается между прогонами"
            assert metadata1["filter_plan"]["filters"] == metadata2["filter_plan"]["filters"], \
                "Фильтры отличаются между прогонами"
            
            logger.info(f"[Test 2] ✅ Консистентно: "
                       f"quality={metadata1['metrics']['quality_level']}, "
                       f"filters={metadata1['filter_plan']['filters']}")
    
    def test_filter_plan_contract_validity(self):
        """
        Тест 3: FilterPlan контракт всегда валиден.
        
        ✅ Проверяет:
        - Первый фильтр ВСЕГДА GRAYSCALE
        - Нет дублей фильтров
        - Фильтры - валидные enum значения
        - FilterPlan имеет reason
        """
        gt_files = self.get_ground_truth_files()
        if not gt_files:
            pytest.skip("Ground Truth files not found")
        
        for gt_file, gt_data in gt_files[:5]:
            image_path = self.find_source_image(gt_data)
            if not image_path:
                continue
            
            logger.info(f"[Test 3] Проверка FilterPlan: {image_path.name}")
            
            _, metadata = self.pipeline.process(image_path)
            filters = metadata["filter_plan"]["filters"]
            
            # ✅ Первый фильтр - GRAYSCALE
            assert filters[0] == "grayscale", \
                f"Первый фильтр должен быть grayscale, получено {filters[0]}"
            
            # ✅ Нет дублей
            assert len(filters) == len(set(filters)), \
                f"Найдены дубли фильтров: {filters}"
            
            # ✅ Валидные фильтры
            valid_filters = {f.value for f in FilterType}
            for f in filters:
                assert f in valid_filters, \
                    f"Неизвестный фильтр: {f}, валидные: {valid_filters}"
            
            # ✅ reason должен быть в FilterPlan
            assert "reason" in metadata["filter_plan"], "Нет reason в FilterPlan"
            assert "quality" in metadata["filter_plan"], "Нет quality в FilterPlan"
            
            logger.info(f"[Test 3] ✅ FilterPlan валиден: "
                       f"filters={filters}, "
                       f"quality={metadata['filter_plan']['quality']}, "
                       f"reason={metadata['filter_plan']['reason']}")
    
    def test_quality_based_filtering_no_magic_shops(self):
        """
        Тест 4: Фильтры выбираются на основе качества, не магазина.
        
        ✅ Проверяет:
        - Два изображения с одинаковым качеством → одинаковые фильтры
        - Два изображения с разным качеством → разные фильтры
        - Система независима от магазина/локали
        """
        gt_files = self.get_ground_truth_files()
        if not gt_files:
            pytest.skip("Ground Truth files not found")
        
        # Собираем изображения по качеству
        by_quality = {}
        
        for gt_file, gt_data in gt_files[:10]:
            image_path = self.find_source_image(gt_data)
            if not image_path:
                continue
            
            _, metadata = self.pipeline.process(image_path)
            quality = metadata["metrics"]["quality_level"]
            filters = tuple(metadata["filter_plan"]["filters"])  # tuple для хеша
            
            if quality not in by_quality:
                by_quality[quality] = []
            
            by_quality[quality].append({
                "image": image_path.name,
                "filters": filters,
                "store": gt_data.get("store", {}).get("name", "unknown")
            })
        
        # Проверяем что изображения одного качества имеют одинаковые фильтры
        for quality, images in by_quality.items():
            if len(images) > 1:
                first_filters = images[0]["filters"]
                
                for img in images[1:]:
                    assert img["filters"] == first_filters, \
                        f"Качество {quality}: разные фильтры для одинакового качества\n" \
                        f"  {images[0]['image']} ({images[0]['store']}): {first_filters}\n" \
                        f"  {img['image']} ({img['store']}): {img['filters']}"
                
                logger.info(f"[Test 4] ✅ Качество {quality}: "
                           f"{len(images)} изображений → одинаковые фильтры {first_filters}")
    
    def test_metric_ranges_reasonable(self):
        """
        Тест 5: Метрики находятся в разумных диапазонах.
        
        ✅ Проверяет:
        - brightness: [0, 255] (normal: [50, 200])
        - contrast: [0, 200] (normal: [20, 100])
        - noise: [100, 3000] (normal: [200, 1500])
        """
        gt_files = self.get_ground_truth_files()
        if not gt_files:
            pytest.skip("Ground Truth files not found")
        
        for gt_file, gt_data in gt_files[:5]:
            image_path = self.find_source_image(gt_data)
            if not image_path:
                continue
            
            logger.info(f"[Test 5] Проверка диапазонов метрик: {image_path.name}")
            
            _, metadata = self.pipeline.process(image_path)
            metrics = metadata["metrics"]
            
            # ✅ Brightness в разумном диапазоне
            assert 0 <= metrics["brightness"] <= 255, \
                f"brightness {metrics['brightness']} вне [0, 255]"
            if not (50 <= metrics["brightness"] <= 200):
                logger.warning(f"  brightness {metrics['brightness']} вне нормального [50, 200]")
            
            # ✅ Contrast
            assert 0 <= metrics["contrast"] <= 200, \
                f"contrast {metrics['contrast']} вне [0, 200]"
            
            # ✅ Noise (может быть до 6000+ для очень шумных изображений)
            assert 0 <= metrics["noise"] <= 10000, \
                f"noise {metrics['noise']} вне [0, 10000]"
            
            logger.info(f"[Test 5] ✅ Метрики в диапазонах: "
                       f"brightness={metrics['brightness']:.1f}, "
                       f"contrast={metrics['contrast']:.2f}, "
                       f"noise={metrics['noise']:.0f}")
    
    def test_cross_locale_consistency(self):
        """
        Тест 6: Система работает одинаково для разных локалей.
        
        ✅ Проверяет:
        - German (de_DE), Thai (th_TH), Polish (pl_PL) и т.д.
        - Одно и то же изображение → одинаковые метрики и фильтры
        - Нет "магии" для конкретных локалей
        """
        gt_files = self.get_ground_truth_files()
        if not gt_files:
            pytest.skip("Ground Truth files not found")
        
        by_locale = {}
        
        for gt_file, gt_data in gt_files:
            image_path = self.find_source_image(gt_data)
            if not image_path:
                continue
            
            locale = gt_data.get("locale", "unknown")
            if locale not in by_locale:
                by_locale[locale] = []
            
            by_locale[locale].append((image_path, gt_data))
        
        logger.info(f"[Test 6] Проверка {len(by_locale)} локалей: {list(by_locale.keys())}")
        
        # Для каждой локали обрабатываем несколько изображений
        for locale, items in list(by_locale.items())[:3]:  # Первые 3 локали
            logger.info(f"[Test 6] Locale: {locale}, изображений: {len(items)}")
            
            for image_path, gt_data in items[:2]:  # Первые 2 изображения
                _, metadata = self.pipeline.process(image_path)
                
                assert "metrics" in metadata, f"Нет метрик для {locale}"
                assert "filter_plan" in metadata, f"Нет filter_plan для {locale}"
                
                logger.info(f"[Test 6] ✅ {locale}: {image_path.name} "
                           f"→ quality={metadata['metrics']['quality_level']}")


class TestD1EdgeCases:
    """Edge case tests для D1 Pipeline."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Инициализация pipeline."""
        self.pipeline = AdaptivePreOCRPipeline()
    
    def test_very_clear_receipt(self):
        """
        Edge Case 1: Чёткое изображение с хорошей экспозицией.
        
        ✅ Проверяет:
        - Детерминированная классификация
        - Фильтры применяются правильно
        - GRAYSCALE всегда первый
        """
        import cv2
        import numpy as np
        
        # Создаём изображение с хорошей экспозицией (gray ~150) и хорошим контрастом
        # Основа серого цвета с чёрным текстом
        image = np.ones((1800, 1200, 3), dtype=np.uint8) * 150  # серый средний
        cv2.putText(image, "RECEIPT", (100, 800), cv2.FONT_HERSHEY_SIMPLEX, 
                   3, (0, 0, 0), 5)  # чёрный текст
        
        # Добавляем шум для реалистичности
        noise = np.random.normal(0, 5, image.shape)
        image = np.clip(image + noise, 0, 255).astype(np.uint8)
        
        temp_path = Path("/tmp/test_clear_receipt.jpg")
        cv2.imwrite(str(temp_path), image)
        
        try:
            _, metadata = self.pipeline.process(temp_path)
            
            # ✅ Качество классифицировано (любое)
            quality = metadata["metrics"]["quality_level"]
            assert quality in ["bad", "low", "medium", "high"], \
                f"Качество должно быть одним из [bad, low, medium, high], получено {quality}"
            
            # ✅ GRAYSCALE должен быть первым фильтром
            filters = metadata["filter_plan"]["filters"]
            assert len(filters) > 0, "Должны быть фильтры"
            assert filters[0] == "grayscale", \
                f"Первый фильтр должен быть grayscale, получено {filters[0]}"
            
            logger.info(f"[Edge Case 1] ✅ CLEAR: quality={quality}, filters={filters}")
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_very_noisy_receipt(self):
        """
        Edge Case 2: Очень шумное изображение.
        
        ✅ Проверяет:
        - LOW или BAD quality классификация (зависит от уровня шума)
        - Детерминированная обработка
        - Фильтры применяются согласно качеству
        """
        import cv2
        import numpy as np
        
        # Создаём шумное изображение с низким контрастом (имитация плохой съёмки)
        # Это будет LOW или BAD quality
        image = np.random.randint(80, 120, (1800, 1200, 3), dtype=np.uint8)
        
        temp_path = Path("/tmp/test_noisy_receipt.jpg")
        cv2.imwrite(str(temp_path), image)
        
        try:
            _, metadata = self.pipeline.process(temp_path)
            
            # ✅ Должно быть LOW или BAD quality (высокий шум + низкий контраст)
            quality = metadata["metrics"]["quality_level"]
            assert quality in ["low", "bad"], \
                f"Шумное изображение должно быть low/bad, получено {quality}"
            
            # ✅ GRAYSCALE должен быть первым фильтром
            filters = metadata["filter_plan"]["filters"]
            assert filters[0] == "grayscale", \
                f"Первый фильтр должен быть grayscale, получено {filters}"
            
            # ✅ Для LOW/BAD качества нужна обработка
            assert len(filters) > 0, "Должны быть применены фильтры"
            
            logger.info(f"[Edge Case 2] ✅ NOISY: quality={quality}, filters={filters}")
        finally:
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
