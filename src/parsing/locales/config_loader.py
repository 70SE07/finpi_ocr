"""
Config Loader для конфигураций локалей парсинга.

ЦКП: Загрузка единой модели LocaleConfig для локали.

Архитектурный принцип:
- Единая модель LocaleConfig для всех локалей
- LocaleConfig = metadata_config + semantic_config
- ConfigLoader загружает и собирает LocaleConfig из YAML файлов
"""

import copy
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, ClassVar
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class MetadataConfig:
    """
    Конфигурация для Stage 4: Metadata Extraction.
    
    Содержит ключевые слова для поиска итоговой суммы.
    """
    total_keywords: List[str]
    detection_keywords: List[str] = field(default_factory=list)


@dataclass
class SemanticConfig:
    """
    Конфигурация для Stage 5: Semantic Extraction.
    
    Содержит все данные для классификации строк:
    - skip_keywords: Слова которые НЕ являются товарами
    - discount_keywords: Слова скидок
    - weight_patterns: Паттерны строк веса (доп. инфо)
    - tax_patterns: Паттерны налоговых строк
    """
    skip_keywords: List[str]
    discount_keywords: List[str]
    weight_patterns: List[str]
    tax_patterns: List[str]
    legal_header_identifiers: List[str] = field(default_factory=list)
    line_split_y_threshold: int = 15      # Пороговая плотность для Stage 5 (BBox split)
    
    # Systemic Configuration Parameters (Configurable Logic)
    clean_outliers_strategy: str = "standard"  # 'none' | 'standard' | 'deep_prefix'
    allow_joined_prices: bool = False          # Разрешить цены без разделителя слева (Text9,99)
    name_buffer_size: int = 3                  # Размер буфера для сохранения имен без цен


@dataclass
class LocaleConfig:
    """
    Единая конфигурация локали для парсинга.
    
    Содержит все необходимые данные для всех этапов пайплайна D2.
    Объединяет MetadataConfig и SemanticConfig.
    Поддерживает обратную совместимость (flat properties).
    """
    locale_code: str
    currency: str
    
    # Stage 4: Metadata
    metadata: MetadataConfig
    
    # Stage 5: Semantic
    semantic: SemanticConfig
    
    # Внутренние поля (кеш и директория)
    _config_dir: Optional[Path] = None
    _cache: ClassVar[Dict[str, "LocaleConfig"]] = {}
    _source_file: Optional[str] = None
    
    # === Backward Compatibility Properties ===
    @property
    def total_keywords(self) -> List[str]:
        return self.metadata.total_keywords
        
    @property
    def detection_keywords(self) -> List[str]:
        return self.metadata.detection_keywords
        
    @property
    def skip_keywords(self) -> List[str]:
        return self.semantic.skip_keywords
        
    @property
    def discount_keywords(self) -> List[str]:
        return self.semantic.discount_keywords
        
    @property
    def weight_patterns(self) -> List[str]:
        return self.semantic.weight_patterns
        
    @property
    def tax_patterns(self) -> List[str]:
        return self.semantic.tax_patterns
        
    @property
    def line_split_y_threshold(self) -> int:
        return self.semantic.line_split_y_threshold

    @classmethod
    def load(cls, locale_code: str, store_name: Optional[str] = None) -> "LocaleConfig":
        """
        Загружает конфигурацию локали и (опционально) магазина.
        """
        cache_key = f"{locale_code}:{store_name.lower() if store_name else ''}"
        
        # Проверяем кеш
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        # 1. Определяем директорию
        if cls._config_dir is None:
            current_file = Path(__file__)
            cls._config_dir = current_file.parent
        
        config_dir = Path(cls._config_dir)
        
        # 2. Загружаем основной конфиг локали
        locale_config = cls._load_locale_yaml(config_dir, locale_code, store_name)
        
        # 3. Сохраняем в кеш
        cls._cache[cache_key] = locale_config
        
        return locale_config

    @classmethod
    def _load_base_config(cls, config_dir: Path) -> dict:
        """Загружает базовую конфигурацию из base.yaml."""
        base_file = config_dir / "base.yaml"
        
        if not base_file.exists():
            logger.warning(f"[ConfigLoader] base.yaml не найден: {base_file}")
            return {}
        
        with open(base_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    @classmethod
    def _resolve_extends(cls, value: Any, base_config: dict) -> Any:
        """
        Обрабатывает ТОЛЬКО выборочное наследование через $extends для списков.
        """
        if isinstance(value, list):
            result = []
            for item in value:
                extended_key = None
                
                if isinstance(item, str) and item.startswith("$extends:"):
                    extended_key = item.split(":", 1)[1].strip()
                elif isinstance(item, dict) and "$extends" in item:
                    extended_key = item["$extends"]
                elif isinstance(item, dict) and "pattern" in item:
                    result.append(item["pattern"])
                    continue
                
                if extended_key:
                    extended = base_config.get(extended_key, [])
                    for ext_item in extended:
                        if isinstance(ext_item, dict) and "pattern" in ext_item:
                            result.append(ext_item["pattern"])
                        else:
                            result.append(ext_item)
                else:
                    result.append(item)
            return result
        return value

    @classmethod
    def _load_locale_yaml(
        cls, 
        config_dir: Path, 
        locale_code: str,
        store_name: Optional[str] = None
    ) -> "LocaleConfig":
        """Загружает конфиг локали с возможным переопределением магазина."""
        # 1. Загружаем base.yaml
        base_config = cls._load_base_config(config_dir)

        # 2. Загружаем локальный конфиг
        config_file = config_dir / locale_code / "parsing.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"[ConfigLoader] Конфиг для {locale_code} не найден")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}

        # 3. Если есть магазин - пробуем загрузить его переопределения
        if store_name:
            store_file = config_dir / locale_code / "stores" / f"{store_name.lower()}.yaml"
            if store_file.exists():
                with open(store_file, 'r', encoding='utf-8') as f:
                    store_data = yaml.safe_load(f) or {}
                    # Мержим: данные магазина имеют приоритет
                    for key, value in store_data.items():
                        if isinstance(value, list) and key in config_data:
                            # Если это список - расширяем или заменяем (по умолчанию расширяем если нет $replace)
                            if value and isinstance(value[0], str) and value[0] == "$replace":
                                config_data[key] = value[1:]
                            else:
                                config_data[key] = config_data[key] + value
                        else:
                            config_data[key] = value
                logger.debug(f"[ConfigLoader] Применены переопределения для магазина: {store_name}")
        
        # Валидация обязательных полей
        if "locale_code" not in config_data:
            raise ValueError(f"[ConfigLoader] Отсутствует locale_code в {config_file}")
        
        if "currency" not in config_data:
            raise ValueError(f"[ConfigLoader] Отсутствует currency в {config_file}")
        
        # Парсим конфигурацию этапов
        total_keywords = cls._resolve_extends(
             config_data.get("total_keywords", ["total"]),
             base_config
        )
        
        metadata_config = MetadataConfig(
            total_keywords=total_keywords,
            detection_keywords=config_data.get("detection_keywords", [])
        )
        
        skip_keywords = cls._resolve_extends(
            config_data.get("skip_keywords", []), 
            base_config
        )
        discount_keywords = cls._resolve_extends(
             config_data.get("discount_keywords", []),
             base_config
        )
        weight_patterns = cls._resolve_extends(
            config_data.get("weight_patterns", []), 
            base_config
        )
        tax_patterns = cls._resolve_extends(
            config_data.get("tax_patterns", []), 
            base_config
        )
        legal_header_identifiers = cls._resolve_extends(
            config_data.get("legal_header_identifiers", []),
            base_config
        )
        
        semantic_config = SemanticConfig(
            skip_keywords=skip_keywords,
            discount_keywords=discount_keywords,
            weight_patterns=weight_patterns,
            tax_patterns=tax_patterns,
            legal_header_identifiers=legal_header_identifiers,
            line_split_y_threshold=config_data.get("line_split_y_threshold", 15),
            # New Systemic Params
            clean_outliers_strategy=config_data.get("clean_outliers_strategy", "standard"),
            allow_joined_prices=config_data.get("allow_joined_prices", False),
            name_buffer_size=config_data.get("name_buffer_size", 3)
        )
        
        return LocaleConfig(
            locale_code=locale_code,
            currency=config_data["currency"],
            metadata=metadata_config,
            semantic=semantic_config,
        )


# Aliases and wrapper
class ConfigLoader:
    def load(self, locale_code: str, store_name: Optional[str] = None) -> "LocaleConfig":
        return LocaleConfig.load(locale_code, store_name)


ParsingConfig = LocaleConfig
