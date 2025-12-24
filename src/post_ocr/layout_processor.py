"""
Layout Element: Упорядочивание и структурирование результатов OCR.

ЦКП: Отсортированный и структурированный список текстовых блоков (TextBlock).
"""

from typing import List
from src.dto import TextBlock, BoundingBox

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
                bbox = BoundingBox(
                    x_min=block["bounding_box"]["x_min"],
                    y_min=block["bounding_box"]["y_min"],
                    x_max=block["bounding_box"]["x_max"],
                    y_max=block["bounding_box"]["y_max"]
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
