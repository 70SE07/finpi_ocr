import pytest
import numpy as np
from src.pre_ocr.elements.image_compressor import ImageCompressor
from config.settings import MAX_IMAGE_SIZE, JPEG_QUALITY

@pytest.fixture
def compressor():
    return ImageCompressor(adaptive=True)

def test_get_target_params_standard(compressor):
    # Стандартное изображение (не длинное, не плотное)
    # Плотность = 0 (пустые байты)
    params = compressor._get_adaptive_settings(1000, 1000, 0)
    assert params == (MAX_IMAGE_SIZE, JPEG_QUALITY)

def test_get_target_params_lidl_style(compressor):
    # Длинный чек (H/W > 2.2)
    # Используем коэффициент из настроек ADAPTIVE_HEIGHT_RATIO
    params = compressor._get_adaptive_settings(500, 2000, 0)
    assert params == (2400, 85)

def test_get_target_params_high_density(compressor):
    # Высокая плотность (байт на пиксель > 0.55)
    params = compressor._get_adaptive_settings(1000, 1000, 1.0)
    assert params == (1800, 85)

def test_compress_returns_numpy(compressor):
    # Создаем фиктивное изображение
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = compressor.compress(img)
    assert result.image is not None
    assert isinstance(result.image, np.ndarray)
    assert result.original_size == (100, 100)
