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
    line_split_y_threshold: int = 15      # Пороговая плотность для Stage 5 (BBox split)


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
    def load(cls, locale_code: str) -> "LocaleConfig":
        """
        Загружает конфигурацию локали из YAML файлов.
        """
        # Проверяем кеш
        if locale_code in cls._cache:
            return cls._cache[locale_code]
        
        # 1. Определяем директорию
        if cls._config_dir is None:
            # Default: относительно файла locale_config.py
            current_file = Path(__file__)
            cls._config_dir = current_file.parent
            cls._source_file = current_file.name
        
        config_dir = Path(cls._config_dir)
        
        # 2. Загружаем конфиг локали
        locale_config = cls._load_locale_yaml(config_dir, locale_code)
        
        # 3. Сохраняем в кеш
        cls._cache[locale_code] = locale_config
        
        logger.debug(
            f"[ConfigLoader] Загружен LocaleConfig для {locale_code}: "
            f"{len(locale_config.metadata.total_keywords)} total_keywords, "
            f"{len(locale_config.semantic.skip_keywords)} skip_keywords"
        )
        
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
        Поддерживает форматы:
        - Строка: "$extends: keys"
        - Словарь: {"$extends": "keys"} (автоматически из YAML без кавычек)
        """
        if isinstance(value, list):
            result = []
            for item in value:
                extended_key = None
                
                # Case 1: String "$extends: key"
                if isinstance(item, str) and item.startswith("$extends:"):
                    extended_key = item.split(":", 1)[1].strip()
                
                # Case 2: Dict {"$extends": "key"}
                elif isinstance(item, dict) and "$extends" in item:
                    extended_key = item["$extends"]
                
                # Case 3: Dict with "pattern" (base.yaml format)
                elif isinstance(item, dict) and "pattern" in item:
                    # Это объект паттерна из base.yaml, нам нужен только regex
                    result.append(item["pattern"])
                    continue
                
                if extended_key:
                    extended = base_config.get(extended_key, [])
                    if not extended:
                        logger.warning(f"[ConfigLoader] Ключ '{extended_key}' для $extends не найден в base.yaml")
                    else:
                        logger.debug(f"[ConfigLoader] Inheriting {len(extended)} items for '{extended_key}'")
                    
                    # Рекурсивно обрабатываем extended (там тоже могут быть dicts)
                    # Но пока просто добавляем, потому что рекурсия для списков тут не реализована
                    # Улучшение: проходимся по extended и извлекаем pattern если есть
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
        locale_code: str
    ) -> "LocaleConfig":
        """Загружает конфиг локали из YAML файла."""
        # 1. Загружаем base.yaml
        base_config = cls._load_base_config(config_dir)

        config_file = config_dir / locale_code / "parsing.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"[ConfigLoader] Конфиг для {locale_code} не найден: {config_file}"
            )
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
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
        metadata_config = MetadataConfig(total_keywords=total_keywords)
        
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
        
        semantic_config = SemanticConfig(
            skip_keywords=skip_keywords,
            discount_keywords=discount_keywords,
            weight_patterns=weight_patterns,
            tax_patterns=tax_patterns,
            line_split_y_threshold=config_data.get("line_split_y_threshold", 15)
        )
        
        return LocaleConfig(
            locale_code=locale_code,
            currency=config_data["currency"],
            metadata=metadata_config,
            semantic=semantic_config,
        )


# Aliases and wrapper
class ConfigLoader:
    """
    Загрузчик конфигураций.
    Обертка над LocaleConfig.load для совместимости с DI.
    """
    def load(self, locale_code: str) -> "LocaleConfig":
        return LocaleConfig.load(locale_code)


ParsingConfig = LocaleConfig
