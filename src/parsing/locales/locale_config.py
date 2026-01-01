"""
Единая модель конфигурации локали для парсинга (LocaleConfig).

ЦКП: Единый объект конфигурации для всех этапов пайплайна D2.

Архитектурный принцип:
- Единство данных — вся конфигурация локали описывается одной моделью
- Расширяемость — добавление новой локали = создание нового YAML файла
- Типобезопасность — Pydantic обеспечивает валидацию типов

Использование:
```python
from src.parsing.locales.locale_config import LocaleConfig

# Загрузка (через LocaleConfig.load())
config = LocaleConfig.load("de_DE")

# Доступ к данным
total_keywords = config.parsing_metadata.total_keywords  # Stage 4
skip_keywords = config.parsing_semantic.skip_keywords     # Stage 5
```
"""

from pydantic import BaseModel, Field
from typing import List



class ParsingMetadataConfig(BaseModel):
    """
    Конфигурация для Stage 4: Metadata Extraction.
    """
    total_keywords: List[str]
    """Ключевые слова для поиска итоговой суммы (по приоритету)."""
    
    currency: str
    """Валюта чека (из локали)."""


class ParsingSemanticConfig(BaseModel):
    """
    Конфигурация для Stage 5: Semantic Extraction.
    """
    skip_keywords: List[str]
    """Слова, которые НЕ являются товарами (skip-слова)."""
    
    discount_keywords: List[str]
    """Слова, которые указывают на скидку."""
    
    weight_patterns: List[str]
    """Паттерны строк веса (доп. информация, не товары)."""
    
    tax_patterns: List[str]
    """Паттерны налоговых строк (A 7%, B 19%)."""


class LocaleConfig(BaseModel):
    """
    Единая конфигурация локали.
    
    Содержит все данные для Stage 4 и Stage 5.
    """
    locale_code: str = Field(..., description="Код локали (например, de_DE, pl_PL)")
    currency: str = Field(..., description="Валюта (EUR, PLN, etc.)")
    
    # Stage 4: Metadata
    parsing_metadata: ParsingMetadataConfig
    
    # Stage 5: Semantic
    parsing_semantic: ParsingSemanticConfig
