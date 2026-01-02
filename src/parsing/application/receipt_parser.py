"""
Основной парсер чеков для домена Parsing, реализующий интерфейс IReceiptParser.

Разделен на специализированные компоненты:
1. LayoutProcessor - обработка структуры
2. LocaleDetector - определение локали
3. MetadataExtractor - извлечение метаданных
4. SemanticExtractor - семантическое извлечение товаров
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from ..domain.interfaces import IReceiptParser, ILayoutProcessor, ILocaleDetector, IMetadataExtractor, ISemanticExtractor
from ..domain.exceptions import ParsingError, LayoutProcessingError, LocaleDetectionError, MetadataExtractionError, SemanticExtractionError
from ..infrastructure.file_manager import ParsingFileManager
from ..dto import OcrResultDTO
from ..locales import LocaleConfigLoader


class ReceiptParser(IReceiptParser):
    """
    Основной парсер чеков домена Parsing с разделенной ответственностью.
    
    Координирует работу специализированных компонентов:
    - Обработка layout
    - Определение локали
    - Извлечение метаданных
    - Семантическое извлечение
    - Сборка результата
    """
    
    def __init__(
        self,
        layout_processor: Optional[ILayoutProcessor] = None,
        locale_detector: Optional[ILocaleDetector] = None,
        metadata_extractor: Optional[IMetadataExtractor] = None,
        semantic_extractor: Optional[ISemanticExtractor] = None,
        file_manager: Optional[ParsingFileManager] = None,
        locale_config_loader: Optional[LocaleConfigLoader] = None,
        save_intermediate: bool = False
    ):
        """
        Инициализация парсера домена Parsing.
        
        Args:
            layout_processor: Процессор layout (опционально)
            locale_detector: Детектор локали (опционально)
            metadata_extractor: Экстрактор метаданных (опционально)
            semantic_extractor: Семантический экстрактор (опционально)
            file_manager: Менеджер файлов (опционально)
            locale_config_loader: Загрузчик конфигурации локали (опционально)
            save_intermediate: Сохранять ли промежуточные результаты
        """
        self.layout_processor = layout_processor
        self.locale_detector = locale_detector
        self.metadata_extractor = metadata_extractor
        self.semantic_extractor = semantic_extractor
        self.file_manager = file_manager
        self.locale_config_loader = locale_config_loader or LocaleConfigLoader()
        self.save_intermediate = save_intermediate
        
        logger.info("[Parsing] ReceiptParser инициализирован")
    
    def parse(self, ocr_data: Dict[str, Any], source_file: str = "", store_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Парсит сырые данные OCR в структурированный формат.
        
        Args:
            ocr_data: Сырые данные OCR (формат raw_ocr)
            source_file: Имя исходного файла
            store_name: Имя магазина (опционально) для загрузки store config
            
        Returns:
            Структурированные данные чека
            
        Raises:
            ParsingError: Если произошла ошибка парсинга
        """
        try:
            logger.info(f"[Parsing] Начало парсинга OCR данных: {source_file}")
            
            # 1. Обработка layout
            logger.debug("[Parsing] Шаг 1: Обработка layout")
            lines = self._process_layout(ocr_data, source_file)
            
            # 2. Определение локали
            logger.debug("[Parsing] Шаг 2: Определение локали")
            locale_code, locale_config = self._detect_locale(lines, source_file, store_name)
            
            # 3. Извлечение метаданных
            logger.debug("[Parsing] Шаг 3: Извлечение метаданных")
            metadata = self._extract_metadata(lines, locale_config, source_file)
            
            # 4. Семантическое извлечение товаров
            logger.debug("[Parsing] Шаг 4: Семантическое извлечение")
            items = self._extract_semantics(lines, locale_config, source_file)
            
            # 5. Сборка финального результата
            logger.debug("[Parsing] Шаг 5: Сборка результата")
            result = self._assemble_result(
                ocr_data=ocr_data,
                lines=lines,
                items=items,
                metadata=metadata,
                locale_code=locale_code,
                source_file=source_file
            )
            
            logger.info(f"[Parsing] Парсинг завершен успешно: {source_file}")
            return result
            
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(
                message=f"Неожиданная ошибка при парсинге: {source_file}",
                component="ReceiptParser",
                original_error=e
            )
    
    def parse_from_file(self, ocr_file_path: Path, store_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Парсит данные OCR из файла.
        
        Args:
            ocr_file_path: Путь к файлу с OCR данными (raw_ocr.json)
            store_name: Имя магазина (опционально) для загрузки store config
            
        Returns:
            Структурированные данные чека
            
        Raises:
            ParsingError: Если произошла ошибка парсинга
        """
        try:
            # Загружаем данные из файла
            if self.file_manager:
                ocr_data = self.file_manager.load_json(ocr_file_path)
            else:
                # Fallback: используем стандартную загрузку
                import json
                with open(ocr_file_path, 'r', encoding='utf-8') as f:
                    ocr_data = json.load(f)
            
            # Извлекаем source_file из metadata или имени файла
            source_file = ocr_data.get("metadata", {}).get("source_file", ocr_file_path.stem)
            
            # Парсим данные
            return self.parse(ocr_data, source_file, store_name)
            
        except Exception as e:
            raise ParsingError(
                message=f"Ошибка при парсинге файла: {ocr_file_path}",
                component="ReceiptParser",
                original_error=e
            )
    
    def _process_layout(self, ocr_data: Dict[str, Any], source_file: str) -> List[Dict[str, Any]]:
        """Обрабатывает layout чека."""
        try:
            if not self.layout_processor:
                # Используем fallback: преобразуем блоки в строки
                from ..parser.result_processor import ResultProcessor
                processor = ResultProcessor()
                lines = processor.process_layout(ocr_data)
                return [line.to_dict() for line in lines]
            
            return self.layout_processor.process(ocr_data)
            
        except Exception as e:
            raise LayoutProcessingError(
                message=f"Ошибка обработки layout: {source_file}",
                component="ReceiptParser",
                original_error=e
            )
    
    def _detect_locale(self, lines: List[Dict[str, Any]], source_file: str, store_name: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
        """
        Определяет локаль чека и загружает конфигурацию.
        
        Args:
            lines: Список строк чека
            source_file: Имя исходного файла
            store_name: Имя магазина (опционально)
        
        Returns:
            tuple[locale_code, locale_config_dict]
        """
        try:
            # Извлекаем тексты из строк
            texts = [line.get('text', '') for line in lines if line.get('text')]
            
            # Определяем локаль
            if self.locale_detector:
                locale_code = self.locale_detector.detect(texts)
            else:
                # Fallback: используем дефолтную локаль
                from ..locales.locale_detector import LocaleDetector
                detector = LocaleDetector()
                locale_code = detector.detect(texts)
            
            # Загружаем конфигурацию локали (с store config если указан)
            locale_config = self.locale_config_loader.load(locale_code, store_name)
            
            logger.debug(f"[Parsing] Определена локаль: {locale_code} ({locale_config.name})")
            if store_name:
                logger.debug(f"[Parsing] Загружен store config: {store_name}")
            
            return locale_code, locale_config.to_dict()
            
        except Exception as e:
            raise LocaleDetectionError(
                message=f"Ошибка определения локали: {source_file}",
                component="ReceiptParser",
                original_error=e
            )
    
    def _extract_metadata(self, lines: List[Dict[str, Any]], locale_config: Dict[str, Any], source_file: str) -> Dict[str, Any]:
        """Извлекает метаданные из чека."""
        try:
            if not self.metadata_extractor:
                # Используем fallback
                from ..metadata.metadata_extractor import MetadataExtractor
                extractor = MetadataExtractor()
                # Нужно преобразовать Dict в объект LocaleConfig
                from ..locales.locale_config import LocaleConfig
                locale_obj = LocaleConfig.from_dict(locale_config)
                result = extractor.process([line.get('text', '') for line in lines], locale_config=locale_obj)
                return result.to_dict()
            
            texts = [line.get('text', '') for line in lines]
            return self.metadata_extractor.extract(texts, locale_config)
            
        except Exception as e:
            raise MetadataExtractionError(
                message=f"Ошибка извлечения метаданных: {source_file}",
                component="ReceiptParser",
                original_error=e
            )
    
    def _extract_semantics(self, lines: List[Dict[str, Any]], locale_config: Dict[str, Any], source_file: str) -> List[Dict[str, Any]]:
        """Извлекает товары из чека."""
        try:
            if not self.semantic_extractor:
                # Используем fallback
                from ..parser.result_processor import ResultProcessor
                processor = ResultProcessor()
                # Нужно преобразовать Dict в объект LocaleConfig
                from ..locales.locale_config import LocaleConfig
                locale_obj = LocaleConfig.from_dict(locale_config)
                
                # Преобразуем Dict обратно в TextBlock
                from ..dto import TextBlock, BoundingBox
                text_blocks = []
                for line in lines:
                    bbox = None
                    if line.get('bounding_box'):
                        bbox_data = line['bounding_box']
                        bbox = BoundingBox(
                            x_min=bbox_data.get('x_min', 0),
                            y_min=bbox_data.get('y_min', 0),
                            x_max=bbox_data.get('x_max', 0),
                            y_max=bbox_data.get('y_max', 0)
                        )
                    text_blocks.append(TextBlock(
                        text=line.get('text', ''),
                        confidence=line.get('confidence', 0.0),
                        bounding_box=bbox,
                        block_type=line.get('block_type', 'TEXT')
                    ))
                
                result = processor.process_extraction(text_blocks, locale_config=locale_obj)
                return result.get('items', [])
            
            return self.semantic_extractor.extract(lines, locale_config)
            
        except Exception as e:
            raise SemanticExtractionError(
                message=f"Ошибка семантического извлечения: {source_file}",
                component="ReceiptParser",
                original_error=e
            )
    
    def _assemble_result(
        self,
        ocr_data: Dict[str, Any],
        lines: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        locale_code: str,
        source_file: str
    ) -> Dict[str, Any]:
        """Собирает финальный результат."""
        try:
            # Извлекаем размеры изображения из metadata raw_ocr
            image_size = (0, 0)
            if "metadata" in ocr_data and "image_size" in ocr_data["metadata"]:
                img_size_data = ocr_data["metadata"]["image_size"]
                if isinstance(img_size_data, (list, tuple)) and len(img_size_data) == 2:
                    image_size = tuple(img_size_data)
            
            # Создаем DTO
            from ..dto import TextBlock, BoundingBox
            text_blocks = []
            for line in lines:
                bbox = None
                if line.get('bounding_box'):
                    bbox_data = line['bounding_box']
                    bbox = BoundingBox(
                        x_min=bbox_data.get('x_min', 0),
                        y_min=bbox_data.get('y_min', 0),
                        x_max=bbox_data.get('x_max', 0),
                        y_max=bbox_data.get('y_max', 0)
                    )
                text_blocks.append(TextBlock(
                    text=line.get('text', ''),
                    confidence=line.get('confidence', 0.0),
                    bounding_box=bbox,
                    block_type=line.get('block_type', 'TEXT')
                ))
            
            dto = OcrResultDTO(
                full_text=ocr_data.get("full_text", ""),
                lines=text_blocks,
                items=items,
                metadata=metadata,
                source_file=source_file,
                pre_ocr_applied=True,
                image_width=image_size[0] if len(image_size) > 0 else 0,
                image_height=image_size[1] if len(image_size) > 1 else 0
            )
            
            # Добавляем информацию о локали
            result_dict = dto.to_dict()
            result_dict["locale"] = locale_code
            
            return result_dict
            
        except Exception as e:
            raise ParsingError(
                message=f"Ошибка сборки результата: {source_file}",
                component="ReceiptParser",
                original_error=e
            )
