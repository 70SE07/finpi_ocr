"""
Интеграционные тесты домена D1 (Extraction).

End-to-end тест: изображение -> D1 -> RawOCRResult с корректной структурой.

ВАЖНО: Эти тесты вызывают реальный Google Vision API и требуют credentials.
"""

import pytest
import re
from pathlib import Path

from src.extraction.pre_ocr import AdaptivePreOCRPipeline
from src.extraction.infrastructure.ocr.google_vision_ocr import GoogleVisionOCR
from src.extraction.application.extraction_pipeline import ExtractionPipeline
from contracts.d1_extraction_dto import RawOCRResult, Word, BoundingBox, OCRMetadata


# Пути к тестовым изображениям
TEST_IMAGE_DE = Path("data/input/IMG_1292.jpeg")  # de_DE
TEST_IMAGE_PL = Path("data/input/PL_001.jpeg")    # pl_PL
TEST_IMAGE_BG = Path("data/input/BG_001.jpeg")    # bg_BG


@pytest.fixture(scope="module")
def extraction_pipeline():
    """
    Fixture: полный ExtractionPipeline с реальными компонентами.
    
    scope="module" - один раз на весь модуль (экономим время инициализации).
    """
    try:
        pre_ocr = AdaptivePreOCRPipeline()
        ocr = GoogleVisionOCR()
        return ExtractionPipeline(ocr_provider=ocr, image_preprocessor=pre_ocr)
    except (ValueError, FileNotFoundError) as e:
        pytest.skip(f"Google Vision credentials not available: {e}")


@pytest.fixture
def test_image_path():
    """Fixture: путь к тестовому изображению de_DE."""
    if not TEST_IMAGE_DE.exists():
        pytest.skip(f"Test image not found: {TEST_IMAGE_DE}")
    return TEST_IMAGE_DE


class TestExtractionPipelineReturnsRawOCRResult:
    """Тесты что D1 возвращает корректный RawOCRResult."""
    
    def test_extraction_pipeline_returns_raw_ocr_result(
        self, extraction_pipeline, test_image_path
    ):
        """D1 должен возвращать экземпляр RawOCRResult."""
        result = extraction_pipeline.process_image(test_image_path)
        
        # Проверка типа
        assert isinstance(result, RawOCRResult), (
            f"Ожидался RawOCRResult, получен {type(result)}"
        )
    
    def test_extraction_pipeline_result_passes_pydantic_validation(
        self, extraction_pipeline, test_image_path
    ):
        """Результат D1 должен проходить Pydantic валидацию."""
        result = extraction_pipeline.process_image(test_image_path)
        
        # Конвертируем в dict и обратно через валидацию
        data = result.model_dump()
        validated = RawOCRResult.model_validate(data)
        
        # Если дошли сюда - валидация прошла
        assert validated is not None


class TestExtractionPipelineWordsNotEmpty:
    """Тесты что words[] не пустой и содержит корректные данные."""
    
    def test_extraction_pipeline_words_not_empty(
        self, extraction_pipeline, test_image_path
    ):
        """words[] не должен быть пустым для реального чека."""
        result = extraction_pipeline.process_image(test_image_path)
        
        assert result.words is not None
        assert isinstance(result.words, list)
        assert len(result.words) > 0, "words[] пустой - OCR не распознал текст"
    
    def test_extraction_pipeline_words_have_correct_structure(
        self, extraction_pipeline, test_image_path
    ):
        """Каждый word в words[] должен иметь text, bounding_box, confidence."""
        result = extraction_pipeline.process_image(test_image_path)
        
        for i, word in enumerate(result.words[:10]):  # Проверяем первые 10
            # Проверка типа
            assert isinstance(word, Word), f"word[{i}] не является Word"
            
            # Проверка text
            assert word.text is not None
            assert len(word.text) > 0, f"word[{i}].text пустой"
            
            # Проверка bounding_box
            assert isinstance(word.bounding_box, BoundingBox)
            assert word.bounding_box.x >= 0
            assert word.bounding_box.y >= 0
            assert word.bounding_box.width > 0
            assert word.bounding_box.height > 0
            
            # Проверка confidence
            assert 0.0 <= word.confidence <= 1.0, (
                f"word[{i}].confidence={word.confidence} вне диапазона [0, 1]"
            )
    
    def test_extraction_pipeline_full_text_not_empty(
        self, extraction_pipeline, test_image_path
    ):
        """full_text не должен быть пустым."""
        result = extraction_pipeline.process_image(test_image_path)
        
        assert result.full_text is not None
        assert isinstance(result.full_text, str)
        assert len(result.full_text) > 0, "full_text пустой"


class TestExtractionPipelineMetadataFilled:
    """Тесты что metadata заполняется корректно."""
    
    def test_extraction_pipeline_metadata_filled(
        self, extraction_pipeline, test_image_path
    ):
        """metadata не должен быть None."""
        result = extraction_pipeline.process_image(test_image_path)
        
        assert result.metadata is not None, "metadata is None"
        assert isinstance(result.metadata, OCRMetadata)
    
    def test_extraction_pipeline_metadata_source_file(
        self, extraction_pipeline, test_image_path
    ):
        """metadata.source_file должен соответствовать входному файлу."""
        result = extraction_pipeline.process_image(test_image_path)
        
        expected_stem = test_image_path.stem
        assert result.metadata.source_file == expected_stem, (
            f"source_file={result.metadata.source_file}, expected={expected_stem}"
        )
    
    def test_extraction_pipeline_metadata_image_dimensions(
        self, extraction_pipeline, test_image_path
    ):
        """metadata.image_width и image_height должны быть > 0."""
        result = extraction_pipeline.process_image(test_image_path)
        
        assert result.metadata.image_width > 0, "image_width <= 0"
        assert result.metadata.image_height > 0, "image_height <= 0"
    
    def test_extraction_pipeline_metadata_processed_at_iso_format(
        self, extraction_pipeline, test_image_path
    ):
        """metadata.processed_at должен быть в формате ISO 8601."""
        result = extraction_pipeline.process_image(test_image_path)
        
        # ISO 8601 паттерн: 2025-01-02T10:30:00.123456
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        assert re.match(iso_pattern, result.metadata.processed_at), (
            f"processed_at не в ISO формате: {result.metadata.processed_at}"
        )


class TestExtractionPipelineMultipleLocales:
    """Тесты на чеках из разных локалей."""
    
    @pytest.mark.parametrize("image_path,locale", [
        (TEST_IMAGE_DE, "de_DE"),
        (TEST_IMAGE_PL, "pl_PL"),
        (TEST_IMAGE_BG, "bg_BG"),
    ])
    def test_extraction_pipeline_works_for_multiple_locales(
        self, extraction_pipeline, image_path, locale
    ):
        """D1 должен работать для чеков из разных локалей."""
        if not image_path.exists():
            pytest.skip(f"Test image not found: {image_path}")
        
        result = extraction_pipeline.process_image(image_path)
        
        # Базовые проверки
        assert isinstance(result, RawOCRResult), f"Locale {locale}: wrong type"
        assert result.has_content(), f"Locale {locale}: no content"
        assert len(result.words) > 0, f"Locale {locale}: words empty"
        assert result.metadata is not None, f"Locale {locale}: no metadata"
