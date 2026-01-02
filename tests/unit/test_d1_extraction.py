"""
Unit тесты для домена D1 (Extraction).

Проверяют:
1. Структура RawOCRResult соответствует контракту
2. Поле называется 'words', а не 'blocks'
3. Metadata заполняется корректно

ВАЖНО: Эти тесты проверяют КОНТРАКТ, не реальный OCR.
"""

import pytest
from datetime import datetime

from contracts.d1_extraction_dto import (
    RawOCRResult,
    Word,
    BoundingBox,
    OCRMetadata,
)


class TestRawOCRResultStructure:
    """Тесты структуры RawOCRResult."""

    def test_raw_ocr_result_has_required_fields(self):
        """RawOCRResult должен иметь поля: full_text, words, metadata."""
        # Создаём минимальный валидный объект
        result = RawOCRResult(
            full_text="Test text",
            words=[],
            metadata=None
        )
        
        # Проверяем наличие полей
        assert hasattr(result, 'full_text')
        assert hasattr(result, 'words')
        assert hasattr(result, 'metadata')
    
    def test_raw_ocr_result_model_dump_structure(self):
        """model_dump() должен возвращать dict с правильными ключами."""
        word = Word(
            text="REWE",
            bounding_box=BoundingBox(x=100, y=50, width=80, height=20),
            confidence=0.98
        )
        
        metadata = OCRMetadata(
            source_file="test_image",
            image_width=800,
            image_height=1200,
            processed_at=datetime.now().isoformat(),
            preprocessing_applied=["grayscale"]
        )
        
        result = RawOCRResult(
            full_text="REWE\nMilch 1,99",
            words=[word],
            metadata=metadata
        )
        
        # Конвертируем в dict (как при сохранении в JSON)
        data = result.model_dump()
        
        # Проверяем структуру
        assert "full_text" in data
        assert "words" in data
        assert "metadata" in data
        
        # Проверяем типы
        assert isinstance(data["full_text"], str)
        assert isinstance(data["words"], list)
        assert isinstance(data["metadata"], dict)


class TestRawOCRResultHasWordsNotBlocks:
    """Тесты что поле называется 'words', а не 'blocks'."""
    
    def test_field_name_is_words(self):
        """Поле должно называться 'words', не 'blocks'."""
        result = RawOCRResult(full_text="", words=[], metadata=None)
        
        # words существует
        assert hasattr(result, 'words')
        
        # blocks НЕ существует
        assert not hasattr(result, 'blocks')
    
    def test_model_dump_has_words_key(self):
        """В JSON должен быть ключ 'words', не 'blocks'."""
        result = RawOCRResult(full_text="", words=[], metadata=None)
        data = result.model_dump()
        
        assert "words" in data
        assert "blocks" not in data
    
    def test_words_contains_word_objects(self):
        """words[] должен содержать Word объекты."""
        word1 = Word(
            text="Milch",
            bounding_box=BoundingBox(x=50, y=100, width=60, height=18),
            confidence=0.95
        )
        word2 = Word(
            text="1,99",
            bounding_box=BoundingBox(x=350, y=100, width=40, height=18),
            confidence=0.97
        )
        
        result = RawOCRResult(
            full_text="Milch 1,99",
            words=[word1, word2],
            metadata=None
        )
        
        assert len(result.words) == 2
        assert result.words[0].text == "Milch"
        assert result.words[1].text == "1,99"


class TestMetadataFilled:
    """Тесты что metadata заполняется корректно."""
    
    def test_metadata_has_required_fields(self):
        """OCRMetadata должен иметь обязательные поля."""
        metadata = OCRMetadata(
            source_file="IMG_1292",
            image_width=800,
            image_height=1200,
            processed_at="2025-01-02T10:30:00",
            preprocessing_applied=[]
        )
        
        assert metadata.source_file == "IMG_1292"
        assert metadata.image_width == 800
        assert metadata.image_height == 1200
        assert metadata.processed_at == "2025-01-02T10:30:00"
        assert metadata.preprocessing_applied == []
    
    def test_metadata_validates_source_file_not_empty(self):
        """source_file не может быть пустым."""
        with pytest.raises(ValueError):
            OCRMetadata(
                source_file="",  # Пустая строка - ошибка
                image_width=800,
                image_height=1200,
                processed_at="2025-01-02T10:30:00"
            )
    
    def test_metadata_validates_image_dimensions_positive(self):
        """image_width и image_height должны быть > 0."""
        with pytest.raises(ValueError):
            OCRMetadata(
                source_file="test",
                image_width=0,  # Ноль - ошибка
                image_height=1200,
                processed_at="2025-01-02T10:30:00"
            )
        
        with pytest.raises(ValueError):
            OCRMetadata(
                source_file="test",
                image_width=800,
                image_height=-1,  # Отрицательное - ошибка
                processed_at="2025-01-02T10:30:00"
            )
    
    def test_metadata_in_raw_ocr_result_not_none(self):
        """При создании через OCR, metadata не должен быть None."""
        # Симулируем создание как в GoogleVisionOCR
        metadata = OCRMetadata(
            source_file="test_file",
            image_width=800,
            image_height=1200,
            processed_at=datetime.now().isoformat(),
            preprocessing_applied=["grayscale", "compression"]
        )
        
        result = RawOCRResult(
            full_text="Test",
            words=[],
            metadata=metadata
        )
        
        assert result.metadata is not None
        assert result.metadata.source_file == "test_file"
        assert result.metadata.image_width > 0
        assert result.metadata.image_height > 0


class TestWordValidation:
    """Тесты валидации Word."""
    
    def test_word_text_not_empty(self):
        """text не может быть пустым."""
        with pytest.raises(ValueError):
            Word(
                text="",  # Пустая строка - ошибка
                bounding_box=BoundingBox(x=0, y=0, width=10, height=10),
                confidence=0.9
            )
    
    def test_word_confidence_in_range(self):
        """confidence должен быть в диапазоне [0.0, 1.0]."""
        # Валидные значения
        Word(text="a", bounding_box=BoundingBox(x=0, y=0, width=1, height=1), confidence=0.0)
        Word(text="a", bounding_box=BoundingBox(x=0, y=0, width=1, height=1), confidence=1.0)
        Word(text="a", bounding_box=BoundingBox(x=0, y=0, width=1, height=1), confidence=0.5)
        
        # Невалидные значения
        with pytest.raises(ValueError):
            Word(text="a", bounding_box=BoundingBox(x=0, y=0, width=1, height=1), confidence=1.1)
        
        with pytest.raises(ValueError):
            Word(text="a", bounding_box=BoundingBox(x=0, y=0, width=1, height=1), confidence=-0.1)


class TestBoundingBoxValidation:
    """Тесты валидации BoundingBox."""
    
    def test_bounding_box_coordinates_non_negative(self):
        """x, y должны быть >= 0."""
        # Валидные
        BoundingBox(x=0, y=0, width=1, height=1)
        BoundingBox(x=100, y=200, width=50, height=30)
        
        # Невалидные
        with pytest.raises(ValueError):
            BoundingBox(x=-1, y=0, width=1, height=1)
        
        with pytest.raises(ValueError):
            BoundingBox(x=0, y=-1, width=1, height=1)
    
    def test_bounding_box_dimensions_positive(self):
        """width, height должны быть > 0."""
        # Валидные
        BoundingBox(x=0, y=0, width=1, height=1)
        
        # Невалидные
        with pytest.raises(ValueError):
            BoundingBox(x=0, y=0, width=0, height=1)
        
        with pytest.raises(ValueError):
            BoundingBox(x=0, y=0, width=1, height=0)
