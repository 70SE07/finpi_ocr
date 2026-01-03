#!/usr/bin/env python3
"""
Скрипт для анализа промежуточных изображений Pre-OCR pipeline.
Сохраняет изображения после каждого stage для визуального анализа шума.
"""

import json
import cv2
from pathlib import Path
from loguru import logger

# Добавляем корень проекта в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import JPEG_QUALITY
from src.extraction.pre_ocr.s0_compression import ImageCompressionStage
from src.extraction.pre_ocr.s1_preparation import ImagePreparationStage
from src.extraction.pre_ocr.infrastructure import apply_grayscale


# 12 чеков из 10 локалей для анализа
GROUND_TRUTH_FILES = [
    "docs/ground_truth/007_bg_BG_billa_BG_001.json",
    "docs/ground_truth/006_cs_CZ_hornbach_cz_001.json",
    "docs/ground_truth/001_de_DE_lidl_IMG_1292.json",
    "docs/ground_truth/013_de_DE_dm_IMG_1252.json",
    "docs/ground_truth/009_en_IN_nybc_IMG_2475.json",
    "docs/ground_truth/003_es_ES_consum_IMG_3064.json",
    "docs/ground_truth/010_pl_PL_carrefour_PL_001.json",
    "docs/ground_truth/004_pt_PT_continente_PT_002.json",
    "docs/ground_truth/002_th_TH_7eleven_IMG_2461.json",
    "docs/ground_truth/061_th_TH_7eleven_IMG_2224.json",
    "docs/ground_truth/008_tr_TR_f33enva_TR_001.json",
    "docs/ground_truth/005_uk_UA_dniprom_UA_001.json",
]

OUTPUT_DIR = Path("data/analysis/pre_ocr_stages")


def get_source_file(gt_path: str) -> str:
    """Извлекает source_file из ground truth JSON."""
    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("source_file", "")


def analyze_receipt(gt_path: str, output_dir: Path):
    """Анализирует один чек и сохраняет промежуточные изображения."""
    
    # Получаем путь к изображению
    source_file = get_source_file(gt_path)
    if not source_file:
        logger.warning(f"No source_file in {gt_path}")
        return
    
    image_path = Path(source_file)
    if not image_path.exists():
        logger.warning(f"Image not found: {image_path}")
        return
    
    # Имя для папки результатов (из ground truth файла)
    gt_name = Path(gt_path).stem  # например: 007_bg_BG_billa_BG_001
    receipt_output_dir = output_dir / gt_name
    receipt_output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Processing: {gt_name}")
    logger.info(f"  Source: {image_path}")
    
    # Stage 1: Preparation (Load image)
    preparation = ImagePreparationStage()
    image = preparation.process(image_path)
    
    # Read original file size
    with open(image_path, 'rb') as f:
        raw_bytes = f.read()
    original_bytes = len(raw_bytes)
    original_shape = image.shape
    logger.info(f"  Original: {original_shape}")
    
    # Сохраняем уменьшенную копию оригинала для сравнения
    cv2.imwrite(str(receipt_output_dir / "0_original.jpg"), image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    
    # Stage 0: Compress
    compressor = ImageCompressionStage(mode='adaptive')
    comp_result = compressor.compress(image, original_bytes=original_bytes)
    compressed_shape = comp_result.image.shape
    logger.info(f"  Compressed: {compressed_shape}")
    cv2.imwrite(str(receipt_output_dir / "1_compressed.jpg"), comp_result.image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    
    # Stage 4: Grayscale
    gray_image = apply_grayscale(comp_result.image)
    gray_shape = gray_image.shape
    logger.info(f"  Grayscale: {gray_shape}")
    cv2.imwrite(str(receipt_output_dir / "2_grayscale.jpg"), gray_image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    
    # Сохраняем метаданные
    metadata = {
        "gt_file": gt_path,
        "source_file": source_file,
        "original_shape": list(original_shape),
        "compressed_shape": list(compressed_shape),
        "grayscale_shape": list(gray_shape),
    }
    with open(receipt_output_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    logger.info(f"  Saved to: {receipt_output_dir}")



def main():
    print("=" * 60)
    print("  Pre-OCR Stages Analysis")
    print("  Анализ промежуточных изображений для 12 чеков")
    print("=" * 60)
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    success = 0
    failed = 0
    
    for gt_path in GROUND_TRUTH_FILES:
        try:
            analyze_receipt(gt_path, OUTPUT_DIR)
            success += 1
        except Exception as e:
            logger.error(f"Failed: {gt_path} - {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"  Готово: {success} успешно, {failed} ошибок")
    print(f"  Результаты в: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
