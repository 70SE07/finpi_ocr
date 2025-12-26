"""
Post-OCR: Структурирование и упорядочивание результатов.

Этап 3 пайплайна:
- Сортировка блоков по позиции (сверху вниз)
- Формирование DTO
- Вычисление статистик
"""

from pathlib import Path
from typing import List, Optional

from ..dto import OcrResultDTO, TextBlock, BoundingBox
from ..layout.layout_processor import LayoutProcessor

# Используем SemanticExtractor напрямую (без адаптера) для избежания круговых импортов
from ..extraction.semantic_extractor import SemanticExtractor


class ResultProcessor:
    """Оркестратор постобработки: координирует Layout и Extraction."""
    
    def __init__(
        self,
        layout: Optional[LayoutProcessor] = None,
        extractor: Optional[SemanticExtractor] = None
    ):
        self.layout = layout or LayoutProcessor()
        self.extractor = extractor or SemanticExtractor()

    def process_layout(self, ocr_result: dict) -> List[TextBlock]:
        """Отдельный этап: Структурный анализ."""
        return self.layout.process(ocr_result.get("blocks", []))

    def process_extraction(self, lines: List[TextBlock], locale_config=None) -> dict:
        """
        Отдельный этап: Семантический анализ.
        
        Args:
            lines: Список текстовых блоков
            locale_config: Конфигурация локали (опционально)
        """
        # Создаем новый SemanticExtractor с locale_config
        from ..extraction.semantic_extractor import SemanticExtractor
        self.extractor = SemanticExtractor(locale_config=locale_config)
        return self.extractor.process(lines)


    def assemble_dto(
        self,
        full_text: str,
        lines: List[TextBlock],
        items: List[dict],
        metadata: Optional[dict] = None,
        source_file: str = "",
        pre_ocr_applied: bool = False,
        image_size: tuple = (0, 0)
    ) -> OcrResultDTO:
        """Финальный этап: Сборка DTO."""
        avg_confidence = self._calculate_average_confidence(lines)
        
        # Преобразуем метаданные в словарь если это объект
        # ВАЖНО: Здесь мы выступаем как Адаптер, сохраняя старые ключи для публичного контракта
        meta_dict = metadata
        if hasattr(metadata, "to_dict"):
            base_dict = metadata.to_dict()
            meta_dict = base_dict.copy()
            # Маппинг для обратной совместимости (Immutable Boundaries)
            if "total_receipt_amount" in base_dict:
                meta_dict["total_amount"] = base_dict["total_receipt_amount"]
                meta_dict["date"] = base_dict["receipt_date"]
                meta_dict["brand"] = base_dict["store_brand"]
                meta_dict["address"] = base_dict["store_address"]
                meta_dict["phone"] = base_dict["store_phone"]
                meta_dict["vat_id"] = base_dict["store_vat_id"]

        return OcrResultDTO(
            full_text=full_text,
            lines=lines,
            items=items,
            metadata=meta_dict or {},
            source_file=source_file,
            ocr_confidence=avg_confidence,
            pre_ocr_applied=pre_ocr_applied,
            post_ocr_applied=True,
            image_width=image_size[0],
            image_height=image_size[1]
        )
    
    def process(
        self,
        ocr_result: dict,
        source_file: str = "",
        pre_ocr_applied: bool = False,
        image_size: tuple = (0, 0)
    ) -> OcrResultDTO:
        """
        Полный цикл Post-OCR (для обратной совместимости).
        """
        lines = self.process_layout(ocr_result)
        extraction_res = self.process_extraction(lines)
        items = extraction_res.get("items", [])
        return self.assemble_dto(
            full_text=ocr_result.get("full_text", ""),
            lines=lines,
            items=items,
            source_file=source_file,
            pre_ocr_applied=pre_ocr_applied,
            image_size=image_size
        )

    def _calculate_average_confidence(self, blocks: List[TextBlock]) -> float:
        """Вычисляет среднюю уверенность по всем блокам."""
        if not blocks:
            return 0.0
        total_confidence = sum(b.confidence for b in blocks)
        return total_confidence / len(blocks)


