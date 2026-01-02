"""
Единая модель конфигурации локали для парсинга (LocaleConfig).

ЦКП: Единый объект конфигурации для всех этапов пайплайна D2.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ParsingMetadataConfig(BaseModel):
    """
    Конфигурация для Stage 4: Metadata Extraction.
    """
    total_keywords: List[str]
    currency: str


class ParsingDetectionConfig(BaseModel):
    """
    Конфигурация для Stage 2: Locale Detection.
    """
    keywords: List[str]


class ParsingSemanticConfig(BaseModel):
    """
    Конфигурация для Stage 5: Semantic Extraction.
    """
    skip_keywords: List[str]
    discount_keywords: List[str]
    weight_patterns: List[str]
    tax_patterns: List[str]
    legal_header_identifiers: List[str]


class LocaleConfig(BaseModel):
    """
    Единая конфигурация локали.
    """
    locale_code: str = Field(..., description="Код локали")
    name: str = Field("Unknown", description="Название страны")
    language: str = Field("en", description="Код языка")
    region: str = Field("US", description="Код региона")
    
    # Stage 2: Detection
    parsing_detection: ParsingDetectionConfig
    
    # Stage 4: Metadata
    parsing_metadata: ParsingMetadataConfig
    
    # Stage 5: Semantic
    parsing_semantic: ParsingSemanticConfig
