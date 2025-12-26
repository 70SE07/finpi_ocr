"""
Адаптер для LayoutProcessor, реализующий интерфейс ILayoutProcessor (домен Parsing).
"""

from typing import Dict, Any, List
from loguru import logger

from ...domain.interfaces import ILayoutProcessor
from ...domain.exceptions import LayoutProcessingError
from ...layout.layout_processor import LayoutProcessor as OriginalLayoutProcessor
from ...parser.result_processor import ResultProcessor


class LayoutProcessorAdapter(ILayoutProcessor):
    """
    Адаптер для LayoutProcessor (домен Parsing).
    
    Реализует интерфейс ILayoutProcessor, делегируя вызовы оригинальному LayoutProcessor
    или используя ResultProcessor как fallback.
    """
    
    def __init__(self, use_result_processor: bool = True):
        """
        Инициализация адаптера.
        
        Args:
            use_result_processor: Использовать ResultProcessor вместо LayoutProcessor
            По умолчанию True, так как ResultProcessor лучше протестирован
        """
        try:
            if use_result_processor:
                self._processor = ResultProcessor()
                self._processor_type = "ResultProcessor"
            else:
                self._processor = OriginalLayoutProcessor()
                self._processor_type = "LayoutProcessor"
            
            logger.debug(f"[Parsing] LayoutProcessorAdapter инициализирован (тип: {self._processor_type})")
        except Exception as e:
            raise LayoutProcessingError(
                message="Не удалось инициализировать LayoutProcessor",
                component="LayoutProcessorAdapter",
                original_error=e
            )
    
    def process(self, ocr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Обрабатывает layout чека.
        
        Args:
            ocr_data: Сырые данные OCR (формат raw_ocr)
            
        Returns:
            Список строк чека с метаданными
            
        Raises:
            LayoutProcessingError: Если произошла ошибка обработки
        """
        try:
            logger.debug(f"[Parsing] Обработка layout (тип процессора: {self._processor_type})")
            
            if self._processor_type == "ResultProcessor":
                # ResultProcessor возвращает список объектов TextBlock
                lines = self._processor.process_layout(ocr_data)
                # Конвертируем TextBlock в словари
                return [line.to_dict() for line in lines]
            else:
                # OriginalLayoutProcessor.process() ожидает List[dict] блоков
                blocks = ocr_data.get('blocks', [])
                if not blocks:
                    logger.warning("[Parsing] Нет блоков для обработки layout")
                    return []
                
                # Вызываем оригинальный метод с правильными аргументами
                result = self._processor.process(blocks)
                
                # OriginalLayoutProcessor возвращает List[TextBlock]
                # Конвертируем TextBlock в словари
                if isinstance(result, list):
                    return [self._convert_to_dict(item) for item in result]
                else:
                    raise LayoutProcessingError(
                        message=f"Неожиданный тип результата: {type(result)}",
                        component="LayoutProcessorAdapter"
                    )
                    
        except Exception as e:
            raise LayoutProcessingError(
                message="Ошибка обработки layout",
                component="LayoutProcessorAdapter",
                original_error=e
            )
    
    def _convert_to_dict(self, item: Any) -> Dict[str, Any]:
        """Конвертирует объект в словарь."""
        from ...dto import TextBlock
        
        if isinstance(item, TextBlock):
            # Используем метод to_dict TextBlock
            return item.to_dict()
        elif hasattr(item, 'to_dict'):
            return item.to_dict()
        elif hasattr(item, '__dict__'):
            return item.__dict__
        else:
            # Пытаемся преобразовать в строку и обратно
            try:
                return {"text": str(item), "raw": item}
            except:
                return {"error": "Не удалось конвертировать объект"}
