"""
Основной пайплайн OCR обработки.

Объединяет три этапа:
1. Pre-OCR: Подготовка изображения
2. OCR: Google Vision распознавание
3. Post-OCR: Структурирование результатов
"""

from pathlib import Path
from typing import Optional, Dict, Any
import sys
import shutil
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    INPUT_DIR, OUTPUT_DIR, SUPPORTED_IMAGE_FORMATS
)
from src.pre_ocr import ImagePreprocessor
from src.ocr import GoogleVisionOCR
from src.post_ocr import ResultProcessor
from src.post_ocr.metadata.metadata_extractor import MetadataExtractor
from src.dto import OcrResultDTO


class OcrPipeline:
    """Полный пайплайн обработки: 5 независимых элементов с группировкой по файлам."""
    
    def __init__(
        self, 
        preprocessor: Optional[ImagePreprocessor] = None,
        ocr: Optional[GoogleVisionOCR] = None,
        result_processor: Optional[ResultProcessor] = None,
        credentials_path: Optional[str] = None
    ):
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.ocr = ocr or GoogleVisionOCR(credentials_path)
        self.result_processor = result_processor or ResultProcessor()
        self.metadata_extractor = MetadataExtractor()
    
    def process_image(
        self,
        image_path: Path,
        save_output: bool = True,
        use_cache: bool = True
    ) -> OcrResultDTO:
        print(f"\n{'='*60}")
        print(f"Обработка: {image_path.name}")
        print(f"{'='*60}")
        
        # Определяем пути вывода для данного файла
        file_out_dir = OUTPUT_DIR / image_path.stem
        pre_ocr_dir = file_out_dir / "pre_ocr"
        raw_ocr_dir = file_out_dir / "raw_ocr"
        post_ocr_dir = file_out_dir / "post_ocr"
        layout_dir = post_ocr_dir / "layout"
        metadata_dir = post_ocr_dir / "metadata"
        items_dir = post_ocr_dir / "items"
        final_dir = post_ocr_dir / "final"

        if save_output:
            for d in [pre_ocr_dir, raw_ocr_dir, layout_dir, metadata_dir, items_dir, final_dir]:
                d.mkdir(parents=True, exist_ok=True)
        
        # --- 1. PRE-OCR ---
        print("\n[1/5] Element: Pre-OCR (Подготовка)...")
        pre_file = pre_ocr_dir / f"{image_path.stem}_preprocessed.jpg"
        
        if use_cache and pre_file.exists():
            print(f"  -> Использовано кэшированное изображение: {pre_file.relative_to(OUTPUT_DIR)}")
            with open(pre_file, "rb") as f: image_bytes = f.read()
            # Для кэша мы не знаем точный processed_size из pre_metadata, 
            # но для DTO это не критично (или можно сохранять в json)
            pre_metadata = {'processed_size': (0, 0)} 
        else:
            image_bytes, pre_metadata = self.preprocessor.process(image_path)
            if save_output:
                self._clear_dir(pre_ocr_dir)
                with open(pre_file, "wb") as f: f.write(image_bytes)
                print(f"  -> ЦКП сохранено: {pre_file.relative_to(OUTPUT_DIR)}")
            
        # --- 2. OCR ---
        print("\n[2/5] Element: OCR (Распознавание)...")
        raw_file = raw_ocr_dir / f"{image_path.stem}_raw.json"
        
        if use_cache and raw_file.exists():
            print(f"  -> Использован кэшированный ответ OCR: {raw_file.relative_to(OUTPUT_DIR)}")
            with open(raw_file, "r", encoding="utf-8") as f:
                ocr_result = json.load(f)
        else:
            ocr_result = self.ocr.recognize(image_bytes)
            # FAIL FAST: Проверка пустого результата
            if not ocr_result or not ocr_result.get("full_text"):
                raise RuntimeError(f"OCR вернул пустой результат для {image_path.name}. Прекращение обработки.")

            if save_output:
                self._clear_dir(raw_ocr_dir)
                with open(raw_file, "w", encoding="utf-8") as f:
                    json.dump(ocr_result, f, ensure_ascii=False, indent=2)
                print(f"  -> ЦКП сохранено: {raw_file.relative_to(OUTPUT_DIR)}")

        # --- 3. LAYOUT ---
        print("\n[3/5] Element: Layout (Структура)...")
        lines = self.result_processor.process_layout(ocr_result)
        if save_output:
            self._clear_dir(layout_dir)
            out_file = layout_dir / f"{image_path.stem}_layout.json"
            layout_data = {"lines": [l.to_dict() for l in lines]}
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)
            print(f"  -> ЦКП сохранено: {out_file.relative_to(OUTPUT_DIR)}")

        # --- 3.5. METADATA ---
        print("\n[3.5/5] Element: Metadata (Метаданные)...")
        texts = [line.text for line in lines]
        metadata_res = self.metadata_extractor.process(texts)
        if save_output:
            self._clear_dir(metadata_dir)
            out_file = metadata_dir / f"{image_path.stem}_metadata.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(metadata_res.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"  -> ЦКП сохранено: {out_file.relative_to(OUTPUT_DIR)}")

        # --- 4. EXTRACTION ---
        print("\n[4/5] Element: Extraction (Семантика)...")
        extraction_res = self.result_processor.process_extraction(lines)
        items = extraction_res.get("items", [])
        
        if save_output:
            self._clear_dir(items_dir)
            out_file = items_dir / f"{image_path.stem}_items.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(extraction_res, f, ensure_ascii=False, indent=2)
            print(f"  -> ЦКП сохранено: {out_file.relative_to(OUTPUT_DIR)}")

        # --- 5. POST-OCR / FINAL ---
        print("\n[5/5] Element: Finalization (DTO)...")
        dto = self.result_processor.assemble_dto(
            full_text=ocr_result.get("full_text", ""),
            lines=lines,
            items=items,
            metadata=metadata_res,
            source_file=image_path.name,
            pre_ocr_applied=True,
            image_size=pre_metadata['processed_size']
        )
        if save_output:
            self._clear_dir(final_dir)
            paths = dto.save_all(str(final_dir), f"{image_path.stem}_result")
            print(f"  -> ЦКП сохранено: {Path(paths['json']).relative_to(OUTPUT_DIR)}")

        return dto

    def _clear_dir(self, path: Path):
        """Атомарно очищает содержимое папки."""
        if not path.exists():
            return
        for item in path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    def process_directory(
        self,
        input_dir: Optional[Path] = None,
        use_cache: bool = True
    ) -> list:
        """
        Обрабатывает все изображения в директории.
        
        Args:
            input_dir: Директория с изображениями (по умолчанию INPUT_DIR)
            
        Returns:
            list: Список OcrResultDTO
        """
        input_path = input_dir or INPUT_DIR
        
        # Находим все поддерживаемые изображения
        images = []
        for ext in SUPPORTED_IMAGE_FORMATS:
            images.extend(input_path.glob(f"*{ext}"))
            images.extend(input_path.glob(f"*{ext.upper()}"))
        
        if not images:
            print(f"Изображения не найдены в {input_path}")
            print(f"Поддерживаемые форматы: {SUPPORTED_IMAGE_FORMATS}")
            return []
        
        print(f"\nНайдено изображений: {len(images)}")
        
        results = []
        for image_path in sorted(images):
            try:
                dto = self.process_image(image_path, use_cache=use_cache)
                results.append(dto)
            except Exception as e:
                print(f"\nОшибка при обработке {image_path.name}: {e}")
        
        print(f"\n{'='*60}")
        print(f"Обработано успешно: {len(results)} из {len(images)}")
        print(f"{'='*60}")
        
        return results
