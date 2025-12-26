"""
Настройки проекта Finpi OCR.

ВАЖНО: Перед запуском укажите путь к вашему Google Cloud credentials файлу!
"""

import os
from pathlib import Path

# =============================================================================
# ПУТИ ПРОЕКТА
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"




# =============================================================================
# GOOGLE CLOUD VISION API
# =============================================================================
# Путь к JSON-файлу с ключом сервисного аккаунта
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(PROJECT_ROOT / "config" / "google_credentials.json")
)

# =============================================================================
# НАСТРОЙКИ ОБРАБОТКИ
# =============================================================================
# Поддерживаемые форматы изображений
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]

# Язык распознавания (для подсказки OCR)
OCR_LANGUAGE_HINTS = ["de", "en"]  # Немецкий + английский для чеков

# =============================================================================
# НАСТРОЙКИ PRE-OCR
# =============================================================================
# Максимальный размер изображения (по большей стороне)
MAX_IMAGE_SIZE = 2200

# Качество сжатия JPEG (0-100)
JPEG_QUALITY = 85

# Адаптивное сжатие
ADAPTIVE_HEIGHT_RATIO = 2.2      # Соотношение H/W для длинных чеков
ADAPTIVE_DENSITY_THRESHOLD = 0.55 # Плотность байт/пиксель
ADAPTIVE_LONG_RECEIPT_SIZE = 2400  # Размер для длинных чеков
ADAPTIVE_HIGH_DENSITY_SIZE = 1800  # Размер для высокой плотности

# =============================================================================
# НАСТРОЙКИ METADATA / EXTRACTION
# =============================================================================
# Валидация даты: текущий год +/- этот отступ
MAX_YEAR_OFFSET_PAST = 2
MAX_YEAR_OFFSET_FUTURE = 1

# Валидация суммы
TOTAL_AMOUNT_MIN = 0.01
TOTAL_AMOUNT_MAX = 100000.0

# Настройки поиска магазина
STORE_SCAN_LIMIT = 15      # Сколько строк проверять на наличие бренда
STORE_FALLBACK_LIMIT = 8   # Сколько строк проверять в fallback-режиме
MIN_STORE_NAME_LENGTH = 3  # Минимальная длина названия магазина

# Confidence scores для метаданных
ADDRESS_CONFIDENCE_HIGH = 0.85  # Высокая уверенность для адреса
STORE_CONFIDENCE_HIGH = 0.85    # Высокая уверенность для магазина

# =============================================================================
# НАСТРОЙКИ ЛОКАЛИ
# =============================================================================
# Дефолтная локаль, если не удалось определить автоматически
DEFAULT_LOCALE = "de_DE"

# Фолбэк-локаль: используется если дефолтная локаль недоступна
# Например, если DEFAULT_LOCALE = "fr_FR" но конфигурации нет, используется FALLBACK_LOCALE
FALLBACK_LOCALE = "en_US"

# =============================================================================
# ПРОВЕРКА КОНФИГУРАЦИИ
# =============================================================================
def validate_config():
    """Проверяет корректность конфигурации."""
    errors = []
    
    if not GOOGLE_APPLICATION_CREDENTIALS:
        errors.append(
            "GOOGLE_APPLICATION_CREDENTIALS не указан!\n"
            "Укажите путь к JSON-ключу в config/settings.py или через переменную окружения."
        )
    elif not Path(GOOGLE_APPLICATION_CREDENTIALS).exists():
        errors.append(
            f"Файл credentials не найден: {GOOGLE_APPLICATION_CREDENTIALS}"
        )
    
    if errors:
        raise ValueError("\n".join(errors))
    
    # Создаём директории если не существуют
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    return True
