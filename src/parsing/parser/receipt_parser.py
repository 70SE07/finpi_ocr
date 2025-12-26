"""
Главный парсер для домена parsing.

Обрабатывает raw_ocr_results.json и извлекает структурированные данные.
"""

from pathlib import Path
from typing import Optional
import json

from ..layout.layout_processor import LayoutProcessor
from ..extraction.semantic_extractor import SemanticExtractor
from ..metadata.metadata_extractor import MetadataExtractor
from ..parser.result_processor import ResultProcessor
from ..dto import OcrResultDTO
from ..locales import LocaleDetector, LocaleConfigLoader
from loguru import logger


class ReceiptParser:
    """
    Главный парсер домена parsing.
    
    Принимает raw_ocr_results.json и возвращает структурированный OcrResultDTO.
    """
    
    def __init__(
        self,
        layout: Optional[LayoutProcessor] = None,
        result_processor: Optional[ResultProcessor] = None,
        locale_detector: Optional[LocaleDetector] = None,
        locale_config_loader: Optional[LocaleConfigLoader] = None,
        metadata_extractor: Optional[MetadataExtractor] = None
    ):
        self.layout = layout or LayoutProcessor()
        self.result_processor = result_processor or ResultProcessor()
        self.locale_detector = locale_detector or LocaleDetector()
        self.locale_config_loader = locale_config_loader or LocaleConfigLoader()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()
    
    def parse_from_file(
        self,
        raw_ocr_path: Path,
        save_output: bool = True,
        output_dir: Optional[Path] = None
    ) -> OcrResultDTO:
        """
        Парсит raw_ocr_results.json файл.
        
        Args:
            raw_ocr_path: Путь к raw_ocr_results.json
            save_output: Сохранять ли промежуточные результаты
            output_dir: Директория для сохранения (если None, берется из raw_ocr_path)
            
        Returns:
            OcrResultDTO: Структурированный результат
        """
        # Читаем raw_ocr JSON
        with open(raw_ocr_path, "r", encoding="utf-8") as f:
            raw_ocr_data = json.load(f)
        
        # Извлекаем source_file из metadata или из имени файла
        source_file = raw_ocr_data.get("metadata", {}).get("source_file", raw_ocr_path.stem)
        
        return self.parse(raw_ocr_data, source_file=source_file, save_output=save_output, output_dir=output_dir)
    
    def parse(
        self,
        raw_ocr_data: dict,
        source_file: str = "",
        save_output: bool = True,
        output_dir: Optional[Path] = None
    ) -> OcrResultDTO:
        """
        Парсит raw_ocr данные (dict).
        
        Args:
            raw_ocr_data: Словарь с raw_ocr данными (формат из extraction домена)
            source_file: Имя исходного файла
            save_output: Сохранять ли промежуточные результаты
            output_dir: Директория для сохранения
            
        Returns:
            OcrResultDTO: Структурированный результат
        """
        print(f"\n{'='*60}")
        print(f"Парсинг: {source_file}")
        print(f"{'='*60}")
        
        # Определяем пути вывода
        if output_dir is None:
            # Пытаемся определить из source_file или используем дефолт
            from config.settings import OUTPUT_DIR
            output_dir = OUTPUT_DIR / source_file
        
        post_ocr_dir = output_dir / "post_ocr"
        layout_dir = post_ocr_dir / "layout"
        metadata_dir = post_ocr_dir / "metadata"
        items_dir = post_ocr_dir / "items"
        final_dir = post_ocr_dir / "final"
        
        if save_output:
            for d in [layout_dir, metadata_dir, items_dir, final_dir]:
                d.mkdir(parents=True, exist_ok=True)
        
        # --- 1. LAYOUT ---
        print("\n[1/4] Layout (Структура)...")
        lines = self.result_processor.process_layout(raw_ocr_data)
        if save_output:
            from shutil import rmtree
            if layout_dir.exists():
                rmtree(layout_dir)
            layout_dir.mkdir(parents=True, exist_ok=True)
            out_file = layout_dir / f"{source_file}_layout.json"
            layout_data = {"lines": [l.to_dict() for l in lines]}
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)
            print(f"  -> Сохранено: {out_file.relative_to(output_dir.parent)}")
        
        # --- 2. LOCALE DETECTION ---
        print("\n[2/4] Locale Detection (Автоопределение локали)...")
        texts = [line.text for line in lines]
        locale_code = self.locale_detector.detect(texts)
        print(f"  -> Определена локаль: {locale_code}")
        
        # --- 3. LOAD LOCALE CONFIG ---
        print("\n[3/4] Locale Config (Загрузка)...")
        locale_config = self.locale_config_loader.load(locale_code)
        print(f"  -> Загружен конфиг для {locale_config.name} ({locale_config.code})")
        
        # Сохраняем информацию о локали
        if save_output:
            locale_file = post_ocr_dir / "locale_info.json"
            with open(locale_file, "w", encoding="utf-8") as f:
                json.dump(locale_config.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"  -> Сохранено: {locale_file.relative_to(output_dir.parent)}")
        
        # --- 4. METADATA ---
        print("\n[4/5] Metadata (Метаданные)...")
        metadata_res = self.metadata_extractor.process(texts, locale_config=locale_config)
        if save_output:
            from shutil import rmtree
            if metadata_dir.exists():
                rmtree(metadata_dir)
            metadata_dir.mkdir(parents=True, exist_ok=True)
            out_file = metadata_dir / f"{source_file}_metadata.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(metadata_res.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"  -> Сохранено: {out_file.relative_to(output_dir.parent)}")
        
        # --- 5. EXTRACTION ---
        print("\n[5/5] Extraction (Семантика)...")
        extraction_res = self.result_processor.process_extraction(lines, locale_config=locale_config)
        items = extraction_res.get("items", [])
        
        if save_output:
            from shutil import rmtree
            if items_dir.exists():
                rmtree(items_dir)
            items_dir.mkdir(parents=True, exist_ok=True)
            out_file = items_dir / f"{source_file}_items.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(extraction_res, f, ensure_ascii=False, indent=2)
            print(f"  -> Сохранено: {out_file.relative_to(output_dir.parent)}")
        
        # --- 6. FINAL ---
        print("\n[6/6] Finalization (DTO)...")
        # Извлекаем размеры изображения из metadata raw_ocr (если есть)
        image_size = (0, 0)
        if "metadata" in raw_ocr_data and "image_size" in raw_ocr_data["metadata"]:
            img_size_data = raw_ocr_data["metadata"]["image_size"]
            if isinstance(img_size_data, (list, tuple)) and len(img_size_data) == 2:
                image_size = tuple(img_size_data)
        
        dto = self.result_processor.assemble_dto(
            full_text=raw_ocr_data.get("full_text", ""),
            lines=lines,
            items=items,
            metadata=metadata_res,
            source_file=source_file,
            pre_ocr_applied=True,  # raw_ocr всегда предполагает pre-ocr
            image_size=image_size
        )
        
        if save_output:
            from shutil import rmtree
            if final_dir.exists():
                rmtree(final_dir)
            final_dir.mkdir(parents=True, exist_ok=True)
            paths = dto.save_all(str(final_dir), f"{source_file}_result")
            print(f"  -> Сохранено: {Path(paths['json']).relative_to(output_dir.parent)}")
        
        return dto


