import pytest
import numpy as np
from src.extraction.pre_ocr.elements.grayscale import GrayscaleConverter


@pytest.fixture
def converter():
    """Fixture для GrayscaleConverter."""
    return GrayscaleConverter()


def test_convert_rgb_to_grayscale(converter):
    """Тест: конвертация RGB (3 канала) → Grayscale (1 канал)."""
    # Создаем RGB изображение (100x100x3)
    rgb_image = np.zeros((100, 100, 3), dtype=np.uint8)
    rgb_image[:, :, 0] = 100  # Blue channel
    rgb_image[:, :, 1] = 150  # Green channel
    rgb_image[:, :, 2] = 200  # Red channel
    
    result = converter.process(rgb_image)
    
    # Проверка: результат - Grayscale (100x100), 1 канал
    assert result.image.shape == (100, 100)
    assert len(result.image.shape) == 2  # Grayscale = 2D array
    assert result.was_converted is True
    assert result.original_channels == 3
    assert result.original_size == (100, 100)
    # Проверка: извлечен Blue канал (первый канал BGR)
    assert np.array_equal(result.image, rgb_image[:, :, 0])


def test_already_grayscale_passes_unchanged(converter):
    """Тест: уже Grayscale изображение проходит без изменений."""
    # Создаем Grayscale изображение (100x100)
    gray_image = np.zeros((100, 100), dtype=np.uint8)
    gray_image[:] = 128
    
    result = converter.process(gray_image)
    
    # Проверка: результат остается Grayscale, не конвертируется
    assert result.image.shape == (100, 100)
    assert len(result.image.shape) == 2
    assert result.was_converted is False
    assert result.original_channels == 1
    assert result.original_size == (100, 100)
    # Проверка: изображение не изменилось
    assert np.array_equal(result.image, gray_image)


def test_convert_bgra_to_grayscale(converter):
    """Тест: BGRA (4 канала) → Grayscale (1 канал)."""
    # Создаем BGRA изображение (100x100x4)
    bgra_image = np.zeros((100, 100, 4), dtype=np.uint8)
    bgra_image[:, :, 0] = 100  # Blue channel
    bgra_image[:, :, 1] = 150  # Green channel
    bgra_image[:, :, 2] = 200  # Red channel
    bgra_image[:, :, 3] = 255  # Alpha channel
    
    result = converter.process(bgra_image)
    
    # Проверка: результат - Grayscale (100x100), 1 канал
    assert result.image.shape == (100, 100)
    assert len(result.image.shape) == 2
    assert result.was_converted is True
    assert result.original_channels == 4
    assert result.original_size == (100, 100)
    # Проверка: извлечен Blue канал (первый канал BGRA)
    assert np.array_equal(result.image, bgra_image[:, :, 0])


def test_size_not_changed(converter):
    """Тест: размер изображения не меняется после конвертации."""
    # Создаем большое RGB изображение (2000x1500x3)
    large_rgb_image = np.zeros((1500, 2000, 3), dtype=np.uint8)
    large_rgb_image[:, :, 0] = 128
    
    result = converter.process(large_rgb_image)
    
    # Проверка: размер не меняется
    assert result.original_size == (2000, 1500)
    assert result.image.shape == (1500, 2000)  # height x width
    assert result.was_converted is True
