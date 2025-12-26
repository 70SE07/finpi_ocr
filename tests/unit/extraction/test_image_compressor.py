import pytest
import numpy as np
from src.extraction.pre_ocr.elements.image_compressor import ImageCompressor
from config.settings import MAX_IMAGE_SIZE, JPEG_QUALITY

@pytest.fixture
def compressor():
    return ImageCompressor(mode="adaptive")

def test_compress_returns_numpy(compressor):
    # Создаем фиктивное изображение
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Вычисляем примерный размер в байтах (100*100*3 = 30000 байт)
    original_bytes = 100 * 100 * 3
    result = compressor.compress(img, original_bytes)
    assert result.image is not None
    assert isinstance(result.image, np.ndarray)
    assert result.original_size == (100, 100)

def test_compress_adaptive_mode(compressor):
    # Тестируем адаптивный режим
    img = np.zeros((2000, 1000, 3), dtype=np.uint8)  # Большое изображение
    original_bytes = 2000 * 1000 * 3  # ~6MB
    result = compressor.compress(img, original_bytes)
    assert result.was_compressed is True
    assert result.method == "adaptive"

def test_compress_fixed_mode():
    # Тестируем фиксированный режим
    compressor_fixed = ImageCompressor(mode="fixed")
    img = np.zeros((3000, 2000, 3), dtype=np.uint8)  # Очень большое изображение
    original_bytes = 3000 * 2000 * 3
    result = compressor_fixed.compress(img, original_bytes)
    assert result.was_compressed is True
    assert result.method == "fixed"
    # В фиксированном режиме размер должен быть ограничен MAX_IMAGE_SIZE
    assert result.compressed_size[0] <= MAX_IMAGE_SIZE

def test_compress_none_mode():
    # Тестируем режим без сжатия
    compressor_none = ImageCompressor(mode="none")
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    original_bytes = 500 * 500 * 3
    result = compressor_none.compress(img, original_bytes)
    assert result.was_compressed is False
    assert result.method == "none"
    assert result.compressed_size == (500, 500)