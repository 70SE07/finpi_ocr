# Finpi OCR - Тренировочный стенд

Лабораторный стенд для экспериментов с Google Vision OCR и обработкой чеков.

## Структура проекта

```
Finpi_OCR/
├── config/
│   ├── settings.py              # Настройки (API ключи, параметры)
│   └── google_credentials.json  # Google Cloud credentials (НЕ в git!)
├── data/
│   ├── input/                   # Входные изображения чеков
│   └── output/
│       └── raw_ocr/             # Сырые результаты OCR (JSON)
├── src/
│   ├── pre_ocr/                 # Этап 1: Предобработка
│   │   ├── image_compressor.py  # Сжатие (2200px / 85%)
│   │   ├── grayscale.py         # Конвертация в ч/б
│   │   ├── future/              # Отложенные модули
│   │   └── old_project/         # Модули из старого проекта
│   ├── ocr/                     # Этап 2: OCR
│   │   └── google_vision_ocr.py # Google Vision API
│   └── post_ocr/                # Этап 3: Постобработка (TODO)
├── scripts/
│   ├── experiments/             # A/B тесты и эксперименты
│   └── run_pipeline.py          # Точка входа
├── docs/
│   └── hypotheses/              # Гипотезы для тестирования
└── requirements.txt
```

## Быстрый старт

### 1. Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка Google Cloud credentials

1. Положите `google_credentials.json` в `config/`
2. Проверьте настройки в `config/settings.py`:

```python
MAX_IMAGE_SIZE = 2200  # Максимальный размер (px)
JPEG_QUALITY = 85      # Качество сжатия
```

### 3. Запуск OCR

```python
from pathlib import Path
from src.ocr.google_vision_ocr import GoogleVisionOCR

ocr = GoogleVisionOCR()
result, json_path = ocr.recognize_from_file_and_save(Path("data/input/receipt.jpg"))

print(f"Сохранено: {json_path}")
```

## Пайплайн

```
[Изображение] → [Pre-OCR] → [OCR] → [raw_ocr/] → [Post-OCR]
                    ↓           ↓         ↓
                Compress    Google    JSON файл
                Grayscale   Vision    с результатом
```

### Настройки Pre-OCR

| Параметр | Значение | Описание |
|----------|----------|----------|
| MAX_IMAGE_SIZE | 2200px | Максимальный размер стороны |
| JPEG_QUALITY | 85% | Качество сжатия |

## Формат raw_ocr

```json
{
  "metadata": {
    "timestamp": "2025-12-23T14:54:27",
    "source_file": "IMG_1292"
  },
  "full_text": "Полный текст чека...",
  "blocks": [
    {
      "text": "Строка текста",
      "confidence": 0.98,
      "bounding_box": {"x_min": 10, "y_min": 20, "x_max": 200, "y_max": 40},
      "block_type": "PARAGRAPH"
    }
  ],
  "raw_annotations": [...]
}
```

## Отложенные модули

В `src/pre_ocr/future/`:
- `deskew_cv.py` — CV-based выравнивание (без OCR)
- `receipt_crop.py` — Обрезка чека

В `src/pre_ocr/old_project/`:
- `deskew_ocr.py` — OCR-based выравнивание (из старого проекта)
