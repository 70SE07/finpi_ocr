"""
Layout Element: Упорядочивание и структурирование результатов OCR.

ЦКП: Отсортированный и структурированный список текстовых блоков (TextBlock).
"""

from typing import List
from ..dto import TextBlock, BoundingBox

class LayoutProcessor:
    """Отвечает за структурный анализ (Layout) распознанного текста."""
    
    def process(self, blocks_raw: List[dict]) -> List[TextBlock]:
        """
        Преобразует сырые блоки в структурированные TextBlock и сортирует их.
        
        Args:
            blocks_raw: Список словарей 'blocks' из результата OCR
            
        Returns:
            List[TextBlock]: Упорядоченные блоки
        """
        # 1. Парсинг
        blocks = self._parse_blocks(blocks_raw)
        
        # 2. Сортировка (Layout Analysis)
        sorted_blocks = self._sort_by_position(blocks)
        
        return sorted_blocks

    def _parse_blocks(self, blocks: List[dict]) -> List[TextBlock]:
        """Преобразует сырые блоки в TextBlock объекты."""
        result = []
        for block in blocks:
            bbox = None
            if block.get("bounding_box"):
                bbox_data = block["bounding_box"]
                # Поддерживаем оба формата: x_min/y_min/x_max/y_max и x/y/width/height
                if "x_min" in bbox_data and "y_min" in bbox_data:
                    # Формат x_min/y_min/x_max/y_max
                    bbox = BoundingBox(
                        x_min=bbox_data["x_min"],
                        y_min=bbox_data["y_min"],
                        x_max=bbox_data["x_max"],
                        y_max=bbox_data["y_max"]
                    )
                elif "x" in bbox_data and "y" in bbox_data:
                    # Формат x/y/width/height (из contracts.RawOCRResult)
                    x = bbox_data["x"]
                    y = bbox_data["y"]
                    width = bbox_data.get("width", 0)
                    height = bbox_data.get("height", 0)
                    bbox = BoundingBox(
                        x_min=int(x),
                        y_min=int(y),
                        x_max=int(x + width),
                        y_max=int(y + height)
                    )
            
            result.append(TextBlock(
                text=block["text"],
                confidence=block.get("confidence", 0.0),
                bounding_box=bbox,
                block_type=block.get("block_type", "TEXT")
            ))
        return result

    def _sort_by_position(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """Сортирует блоки по позиции: сверху вниз, слева направо."""
        def sort_key(block: TextBlock):
            if block.bounding_box:
                return (block.bounding_box.y_min, block.bounding_box.x_min)
            return (0, 0)
        
        return sorted(blocks, key=sort_key)


