#!/usr/bin/env python3
"""
Интеграционные тесты D2 против Ground Truth.

Цель: Проверить что ParsingPipeline (stages/) корректно парсит все чеки
из Ground Truth. Основная метрика - checksum (сумма товаров == итог чека).

Тест НЕ ИСПОЛЬЗУЕТ МОКИ - работает с реальными файлами.
"""

import json
import pytest
from pathlib import Path
from typing import List, Tuple

import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from contracts.d1_extraction_dto import RawOCRResult
from src.parsing.stages.pipeline import ParsingPipeline


# Директории
GROUND_TRUTH_DIR = PROJECT_ROOT / "docs" / "ground_truth"
DATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def load_ground_truth_files() -> List[Tuple[str, dict]]:
    """Загружает все Ground Truth файлы."""
    gt_files = []
    for gt_file in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        if gt_file.name == "README.md":
            continue
        try:
            with open(gt_file, "r", encoding="utf-8") as f:
                gt_data = json.load(f)
            gt_files.append((gt_file.stem, gt_data))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {gt_file}: {e}")
    return gt_files


def find_raw_ocr_for_gt(gt_data: dict) -> Path | None:
    """Находит raw_ocr_results.json для Ground Truth файла."""
    source_file = gt_data.get("source_file", "")
    if not source_file:
        return None
    
    # Извлекаем имя файла без расширения
    # source_file может быть "data/input/PL_001.jpeg"
    filename = Path(source_file).stem
    
    # Ищем в data/output/{filename}/raw_ocr_results.json
    raw_ocr_path = DATA_OUTPUT_DIR / filename / "raw_ocr_results.json"
    if raw_ocr_path.exists():
        return raw_ocr_path
    
    return None


def load_raw_ocr(path: Path) -> RawOCRResult | None:
    """Загружает RawOCRResult из файла."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RawOCRResult.model_validate(data)
    except Exception as e:
        print(f"Warning: Could not load {path}: {e}")
        return None


# Собираем все Ground Truth файлы для параметризации
GT_FILES = load_ground_truth_files()


@pytest.mark.integration
class TestD2GroundTruth:
    """Тесты D2 против Ground Truth."""
    
    def setup_method(self):
        """Создаём пайплайн перед каждым тестом."""
        self.pipeline = ParsingPipeline()
    
    @pytest.mark.parametrize("gt_name,gt_data", GT_FILES, ids=[x[0] for x in GT_FILES])
    def test_checksum_validation(self, gt_name: str, gt_data: dict):
        """
        Тест checksum: SUM(items.total_price) == receipt_total.
        
        Это PRIMARY метрика качества парсинга. Если checksum не сходится,
        значит парсер что-то пропустил или неправильно распарсил.
        """
        # Находим raw_ocr для этого GT
        raw_ocr_path = find_raw_ocr_for_gt(gt_data)
        if raw_ocr_path is None:
            pytest.skip(f"No raw_ocr_results.json found for {gt_name}")
        
        raw_ocr = load_raw_ocr(raw_ocr_path)
        if raw_ocr is None:
            pytest.skip(f"Could not load raw_ocr from {raw_ocr_path}")
        
        # Запускаем пайплайн
        result = self.pipeline.process(raw_ocr)
        
        # Проверяем validation
        assert result.validation is not None, f"{gt_name}: Validation stage did not run"
        
        # Основная проверка - checksum должен сходиться
        if not result.validation.passed:
            # Собираем детали для отчёта
            diff = result.validation.difference
            items_sum = result.validation.items_sum
            receipt_total = result.validation.receipt_total
            
            pytest.fail(
                f"{gt_name}: Checksum FAILED\n"
                f"  Items sum: {items_sum}\n"
                f"  Receipt total: {receipt_total}\n"
                f"  Difference: {diff}\n"
                f"  Items count: {len(result.dto.items) if result.dto else 0}"
            )
    
    @pytest.mark.parametrize("gt_name,gt_data", GT_FILES, ids=[x[0] for x in GT_FILES])
    def test_items_count(self, gt_name: str, gt_data: dict):
        """
        Тест количества товаров.
        
        Проверяет что количество распознанных товаров близко к GT.
        Допускается погрешность +-2 товара из-за OCR шума.
        """
        raw_ocr_path = find_raw_ocr_for_gt(gt_data)
        if raw_ocr_path is None:
            pytest.skip(f"No raw_ocr_results.json found for {gt_name}")
        
        raw_ocr = load_raw_ocr(raw_ocr_path)
        if raw_ocr is None:
            pytest.skip(f"Could not load raw_ocr from {raw_ocr_path}")
        
        # GT items count
        gt_items = gt_data.get("items", [])
        gt_count = len(gt_items)
        
        # Пропускаем если в GT нет items
        if gt_count == 0:
            pytest.skip(f"{gt_name}: No items in Ground Truth")
        
        # Запускаем пайплайн
        result = self.pipeline.process(raw_ocr)
        
        parsed_count = len(result.dto.items) if result.dto else 0
        
        # Допускаем погрешность +-2 товара
        tolerance = 2
        assert abs(parsed_count - gt_count) <= tolerance, (
            f"{gt_name}: Items count mismatch\n"
            f"  Ground Truth: {gt_count}\n"
            f"  Parsed: {parsed_count}\n"
            f"  Tolerance: {tolerance}"
        )
    
    @pytest.mark.parametrize("gt_name,gt_data", GT_FILES, ids=[x[0] for x in GT_FILES])
    def test_total_amount(self, gt_name: str, gt_data: dict):
        """
        Тест извлечения итоговой суммы.
        
        Проверяет что Stage 4 (Metadata) правильно извлёк total.
        """
        raw_ocr_path = find_raw_ocr_for_gt(gt_data)
        if raw_ocr_path is None:
            pytest.skip(f"No raw_ocr_results.json found for {gt_name}")
        
        raw_ocr = load_raw_ocr(raw_ocr_path)
        if raw_ocr is None:
            pytest.skip(f"Could not load raw_ocr from {raw_ocr_path}")
        
        # GT total
        gt_metadata = gt_data.get("metadata", {})
        gt_total = gt_metadata.get("receipt_total")
        
        if gt_total is None:
            pytest.skip(f"{gt_name}: No receipt_total in Ground Truth")
        
        # Запускаем пайплайн
        result = self.pipeline.process(raw_ocr)
        
        parsed_total = result.dto.total_amount if result.dto else None
        
        assert parsed_total is not None, f"{gt_name}: Total not extracted"
        
        # Допускаем погрешность 0.05 (округление)
        assert abs(parsed_total - gt_total) < 0.05, (
            f"{gt_name}: Total mismatch\n"
            f"  Ground Truth: {gt_total}\n"
            f"  Parsed: {parsed_total}"
        )


if __name__ == "__main__":
    # Быстрый запуск без pytest
    print(f"Found {len(GT_FILES)} Ground Truth files")
    
    pipeline = ParsingPipeline()
    passed = 0
    failed = 0
    skipped = 0
    
    for gt_name, gt_data in GT_FILES:
        raw_ocr_path = find_raw_ocr_for_gt(gt_data)
        if raw_ocr_path is None:
            skipped += 1
            continue
        
        raw_ocr = load_raw_ocr(raw_ocr_path)
        if raw_ocr is None:
            skipped += 1
            continue
        
        result = pipeline.process(raw_ocr)
        
        if result.validation and result.validation.passed:
            passed += 1
            print(f"  [PASS] {gt_name}")
        else:
            failed += 1
            diff = result.validation.difference if result.validation else "N/A"
            print(f"  [FAIL] {gt_name} (diff: {diff})")
    
    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")
