import pytest
from pathlib import Path
import re

from src.extraction.pre_ocr import AdaptivePreOCRPipeline
from src.extraction.infrastructure.ocr.google_vision_ocr import GoogleVisionOCR
from src.extraction.application.extraction_pipeline import ExtractionPipeline
from contracts.d1_extraction_dto import RawOCRResult


@pytest.fixture
def test_receipt_path():
    """Fixture: путь к тестовому чеку."""
    # Используем реальный чек из проекта
    receipt_path = Path("photo/GOODS/Lidl/IMG_1292.jpeg")
    
    if not receipt_path.exists():
        pytest.skip(f"Test receipt not found: {receipt_path}")
    
    return receipt_path


@pytest.fixture
def pre_ocr_pipeline():
    """Fixture: AdaptivePreOCRPipeline."""
    return AdaptivePreOCRPipeline()


@pytest.fixture
def ocr_provider():
    """Fixture: GoogleVisionOCR с реальными credentials."""
    try:
        return GoogleVisionOCR()
    except (ValueError, FileNotFoundError) as e:
        pytest.skip(f"Google Vision credentials not available: {e}")


@pytest.fixture
def extraction_pipeline(pre_ocr_pipeline, ocr_provider):
    """Fixture: ExtractionPipeline с реальными компонентами."""
    return ExtractionPipeline(
        ocr_provider=ocr_provider,
        image_preprocessor=pre_ocr_pipeline
    )


def test_extraction_returns_valid_raw_ocr_result(extraction_pipeline, test_receipt_path):
    """Тест: D1 возвращает валидный RawOCRResult."""
    # Запустить полный пайплайн D1
    result = extraction_pipeline.process_image(test_receipt_path)
    
    # Проверка: результат - экземпляр RawOCRResult
    assert isinstance(result, RawOCRResult)
    
    # Проверка: Pydantic валидация проходит (если есть ValidationError, он выбросится здесь)
    # Если дошли до этой строки - валидация прошла успешно
    assert result is not None


def test_full_text_not_empty(extraction_pipeline, test_receipt_path):
    """Тест: full_text не пустой."""
    result = extraction_pipeline.process_image(test_receipt_path)
    
    # Проверка: full_text не пустая строка
    assert result.full_text is not None
    assert isinstance(result.full_text, str)
    assert len(result.full_text) > 0


def test_words_not_empty(extraction_pipeline, test_receipt_path):
    """Тест: words не пустой."""
    result = extraction_pipeline.process_image(test_receipt_path)
    
    # Проверка: words не пустой
    assert result.words is not None
    assert isinstance(result.words, list)
    assert len(result.words) > 0
    
    # Проверка: каждый word имеет text, bounding_box, confidence
    for word in result.words:
        assert hasattr(word, 'text')
        assert hasattr(word, 'bounding_box')
        assert hasattr(word, 'confidence')
        assert len(word.text) > 0
        assert word.confidence >= 0.0
        assert word.confidence <= 1.0


def test_metadata_present_and_valid(extraction_pipeline, test_receipt_path):
    """Тест: metadata присутствует и валидна."""
    result = extraction_pipeline.process_image(test_receipt_path)
    
    # Проверка: metadata присутствует
    assert result.metadata is not None
    
    # Проверка: metadata.source_file соответствует входному файлу
    assert result.metadata.source_file == test_receipt_path.stem
    
    # Проверка: metadata.image_width, image_height > 0
    assert result.metadata.image_width > 0
    assert result.metadata.image_height > 0
    
    # Проверка: metadata.processed_at в формате ISO 8601
    # Пример: "2025-01-15T14:30:00.123456"
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
    assert re.match(iso_pattern, result.metadata.processed_at) is not None


def test_has_content_returns_true(extraction_pipeline, test_receipt_path):
    """Тест: has_content() возвращает True для валидного результата."""
    result = extraction_pipeline.process_image(test_receipt_path)
    
    # Проверка: has_content() возвращает True
    assert result.has_content() is True


@pytest.mark.parametrize("receipt_name", [
    "photo/GOODS/Lidl/IMG_1292.jpeg",
    "photo/GOODS/Lidl/IMG_1336.jpeg",
])
def test_multiple_receipts(extraction_pipeline, receipt_name):
    """Параметризованный тест на нескольких чеках."""
    receipt_path = Path(receipt_name)
    
    if not receipt_path.exists():
        pytest.skip(f"Test receipt not found: {receipt_path}")
    
    # Запустить пайплайн
    result = extraction_pipeline.process_image(receipt_path)
    
    # Проверка структурной валидности
    assert isinstance(result, RawOCRResult)
    assert result.has_content() is True
    assert len(result.full_text) > 0
    assert len(result.words) > 0
    assert result.metadata is not None
    assert result.metadata.image_width > 0
    assert result.metadata.image_height > 0
