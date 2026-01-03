import pytest
import tempfile
import cv2
import numpy as np
from pathlib import Path
from src.extraction.pre_ocr.s1_preparation.stage import ImagePreparationStage


@pytest.fixture
def reader():
    """Fixture для ImagePreparationStage."""
    return ImagePreparationStage()


@pytest.fixture
def temp_image_jpeg(tmp_path):
    """Fixture: создает временный JPEG файл для тестов."""
    image_path = tmp_path / "test_image.jpg"
    
    # Создаем простое RGB изображение (100x100x3)
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    test_image[:, :, 0] = 100  # Blue
    test_image[:, :, 1] = 150  # Green
    test_image[:, :, 2] = 200  # Red
    
    # Сохраняем как JPEG
    cv2.imwrite(str(image_path), test_image)
    
    return image_path


@pytest.fixture
def temp_image_png(tmp_path):
    """Fixture: создает временный PNG файл для тестов."""
    image_path = tmp_path / "test_image.png"
    
    # Создаем простое RGB изображение (100x100x3)
    test_image = np.zeros((100, 100, 3), dtype=np.uint8)
    test_image[:, :, 0] = 100  # Blue
    test_image[:, :, 1] = 150  # Green
    test_image[:, :, 2] = 200  # Red
    
    # Сохраняем как PNG
    cv2.imwrite(str(image_path), test_image)
    
    return image_path


@pytest.fixture
def temp_small_image(tmp_path):
    """Fixture: создает маленькое JPEG изображение (10x10)."""
    image_path = tmp_path / "small_image.jpg"
    
    test_image = np.zeros((10, 10, 3), dtype=np.uint8)
    cv2.imwrite(str(image_path), test_image)
    
    return image_path


@pytest.fixture
def temp_large_image(tmp_path):
    """Fixture: создает большое JPEG изображение (2000x1500)."""
    image_path = tmp_path / "large_image.jpg"
    
    test_image = np.zeros((1500, 2000, 3), dtype=np.uint8)
    cv2.imwrite(str(image_path), test_image)
    
    return image_path


@pytest.fixture
def temp_corrupted_file(tmp_path):
    """Fixture: создает файл с некорректными данными."""
    corrupted_path = tmp_path / "corrupted.jpg"
    
    # Записываем некорректные данные
    with open(corrupted_path, "wb") as f:
        f.write(b"This is not a valid image file")
    
    return corrupted_path


def test_read_valid_jpeg(reader, temp_image_jpeg):
    """Тест: успешное чтение валидного JPEG."""
    image, raw_bytes = reader.read(temp_image_jpeg)
    
    # Проверка: возвращает кортеж (numpy.ndarray, bytes)
    assert isinstance(image, np.ndarray)
    assert isinstance(raw_bytes, bytes)
    
    # Проверка: image.shape соответствует изображению
    assert image.shape == (100, 100, 3)  # BGR формат
    assert image.dtype == np.uint8
    
    # Проверка: raw_bytes не пустой
    assert len(raw_bytes) > 0


def test_file_not_found_error(reader, tmp_path):
    """Тест: FileNotFoundError для несуществующего файла."""
    non_existent_path = tmp_path / "non_existent.jpg"
    
    with pytest.raises(FileNotFoundError, match="Image not found"):
        reader.read(non_existent_path)


def test_corrupted_file_error(reader, temp_corrupted_file):
    """Тест: ValueError для поврежденного файла."""
    with pytest.raises(ValueError, match="Failed to decode image"):
        reader.read(temp_corrupted_file)


def test_read_png(reader, temp_image_png):
    """Тест: чтение PNG файла."""
    image, raw_bytes = reader.read(temp_image_png)
    
    # Проверка: PNG успешно читается
    assert isinstance(image, np.ndarray)
    assert image.shape == (100, 100, 3)  # BGR формат
    assert len(raw_bytes) > 0


def test_read_small_image(reader, temp_small_image):
    """Тест: чтение маленького JPEG изображения (10x10)."""
    image, raw_bytes = reader.read(temp_small_image)
    
    assert image.shape == (10, 10, 3)
    assert len(raw_bytes) > 0


def test_read_large_image(reader, temp_large_image):
    """Тест: чтение большого JPEG изображения (2000x1500)."""
    image, raw_bytes = reader.read(temp_large_image)
    
    assert image.shape == (1500, 2000, 3)
    assert len(raw_bytes) > 0
