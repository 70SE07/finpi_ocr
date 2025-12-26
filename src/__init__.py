"""Finpi OCR - тренировочный стенд для Google Vision OCR."""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для чистых импортов
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
