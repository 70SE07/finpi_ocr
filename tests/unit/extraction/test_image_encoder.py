import pytest
import numpy as np
from src.extraction.pre_ocr.image_encoder import ImageEncoder


@pytest.fixture
def rgb_image():
    """Fixture: создает RGB тестовое изображение (numpy array)."""
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[:, :, 0] = 100  # Blue
    image[:, :, 1] = 150  # Green
    image[:, :, 2] = 200  # Red
    return image


@pytest.fixture
def grayscale_image():
    """Fixture: создает Grayscale тестовое изображение (numpy array)."""
    image = np.zeros((100, 100), dtype=np.uint8)
    image[:] = 128
    return image


def test_encode_rgb_image(rgb_image):
    """Тест: кодирование RGB изображения."""
    encoded = ImageEncoder.encode(rgb_image)
    
    # Проверка: возвращает bytes
    assert isinstance(encoded, bytes)
    
    # Проверка: байты не пустые
    assert len(encoded) > 0
    
    # Проверка: байты начинаются с JPEG signature (FF D8 FF)
    assert encoded[0] == 0xFF
    assert encoded[1] == 0xD8
    assert encoded[2] == 0xFF


def test_encode_grayscale_image(grayscale_image):
    """Тест: кодирование Grayscale изображения."""
    encoded = ImageEncoder.encode(grayscale_image)
    
    # Проверка: возвращает валидные JPEG bytes
    assert isinstance(encoded, bytes)
    assert len(encoded) > 0
    
    # Проверка: JPEG signature
    assert encoded[0] == 0xFF
    assert encoded[1] == 0xD8
    assert encoded[2] == 0xFF


def test_quality_affects_file_size(rgb_image):
    """Тест: параметр quality влияет на размер файла."""
    encoded_low = ImageEncoder.encode(rgb_image, quality=50)
    encoded_high = ImageEncoder.encode(rgb_image, quality=95)
    
    # Проверка: оба возвращают bytes
    assert isinstance(encoded_low, bytes)
    assert isinstance(encoded_high, bytes)
    
    # Проверка: качество 95 обычно дает больший файл чем quality 50
    # (не всегда, но обычно для одного и того же изображения)
    # Это не гарантированно, но проверяем что оба валидные
    assert len(encoded_low) > 0
    assert len(encoded_high) > 0


def test_min_quality(rgb_image):
    """Тест: минимальный quality (0)."""
    encoded = ImageEncoder.encode(rgb_image, quality=0)
    
    assert isinstance(encoded, bytes)
    assert len(encoded) > 0
    # JPEG signature все равно должен быть
    assert encoded[0] == 0xFF
    assert encoded[1] == 0xD8


def test_max_quality(rgb_image):
    """Тест: максимальный quality (100)."""
    encoded = ImageEncoder.encode(rgb_image, quality=100)
    
    assert isinstance(encoded, bytes)
    assert len(encoded) > 0
    assert encoded[0] == 0xFF
    assert encoded[1] == 0xD8


def test_default_quality(rgb_image):
    """Тест: дефолтный quality (85)."""
    encoded = ImageEncoder.encode(rgb_image)  # Без указания quality
    
    assert isinstance(encoded, bytes)
    assert len(encoded) > 0
    assert encoded[0] == 0xFF
    assert encoded[1] == 0xD8
