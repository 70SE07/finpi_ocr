"""
DTO для конфигурации локали.

Содержит все специфичные для страны параметры:
- Валюта (форматирование, символы)
- Форматы даты
- Ключевые слова (total, discount, store brands)
- Настройки экстракторов

Использует Pydantic для валидации структуры конфигурации.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional


class CurrencyConfig(BaseModel):
    """Конфигурация валюты."""
    code: str = Field(..., description="ISO код (EUR, USD, PLN, THB)")
    symbol: str = Field(..., description="Символ (€, $, zł, ฿)")
    decimal_separator: str = Field(..., description='Разделитель дроби ("," или ".")')
    thousands_separator: str = Field(..., description='Разделитель тысяч (".", ",", пробел)')
    symbol_position: str = Field(..., description='"before" или "after"')
    format: str = Field(..., description='Пример "1.234,56"')
    
    @field_validator('symbol_position')
    @classmethod
    def validate_symbol_position(cls, v):
        if v not in ["before", "after"]:
            raise ValueError(f'symbol_position должен быть "before" или "after", получено: {v}')
        return v
    
    @field_validator('decimal_separator', 'thousands_separator')
    @classmethod
    def validate_separators(cls, v):
        if v not in [",", ".", " "]:
            raise ValueError(f'Разделитель должен быть одним из [",", ".", " "], получено: {v}')
        return v


class DateConfig(BaseModel):
    """Конфигурация даты."""
    formats: List[str] = Field(
        default_factory=list,
        description='Список форматов дат (например, ["DD.MM.YYYY", "DD.MM.YY"])'
    )
    
    @field_validator('formats')
    @classmethod
    def validate_formats(cls, v):
        if not v:
            raise ValueError('date_formats не может быть пустым')
        return v


class PatternsConfig(BaseModel):
    """Ключевые слова и паттерны."""
    total_keywords: List[str] = Field(
        default_factory=list,
        description='Ключевые слова для определения итоговой суммы'
    )
    discount_keywords: List[str] = Field(
        default_factory=list,
        description='Ключевые слова для скидок'
    )
    noise_keywords: List[str] = Field(
        default_factory=list,
        description='Шумовые слова (игнорируются при поиске магазина)'
    )


class ExtractorConfig(BaseModel):
    """Настройки экстракторов."""
    store_detection: Dict[str, Any] = Field(
        default_factory=dict,
        description='Настройки детектора магазина'
    )
    total_detection: Dict[str, Any] = Field(
        default_factory=dict,
        description='Настройки детектора итоговой суммы'
    )


class LocaleConfig(BaseModel):
    """
    Полная конфигурация локали.
    
    Загружается из YAML файла и используется всеми экстракторами.
    Валидируется через Pydantic для обеспечения целостности структуры.
    """
    # Базовая информация
    code: str = Field(..., description='Код локали (de_DE, pl_PL, th_TH, kz_KZ)')
    name: str = Field(..., description='Название страны (Germany, Poland, Thailand, Kazakhstan)')
    language: str = Field(..., description='Код языка (de, pl, th, kk)')
    region: str = Field(..., description='Код региона (DE, PL, TH, KZ)')
    rtl: bool = Field(default=False, description='Right-to-left (для арабского, иврита)')
    
    # Конфигурации
    currency: Optional[CurrencyConfig] = Field(default=None, description='Конфигурация валюты')
    date: Optional[DateConfig] = Field(default=None, description='Конфигурация даты')
    patterns: Optional[PatternsConfig] = Field(default=None, description='Ключевые слова и паттерны')
    extractors: Optional[ExtractorConfig] = Field(default=None, description='Настройки экстракторов')
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """Валидация формата кода локали (xx_XX)."""
        if '_' not in v:
            raise ValueError(f'Код локали должен быть в формате "xx_XX" (например, de_DE), получено: {v}')
        parts = v.split('_')
        if len(parts) != 2:
            raise ValueError(f'Код локали должен быть в формате "xx_XX", получено: {v}')
        if len(parts[0]) != 2 or len(parts[1]) != 2:
            raise ValueError(f'Код языка и региона должны быть по 2 символа (например, de_DE), получено: {v}')
        return v.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует в словарь для сериализации."""
        result = {
            "code": self.code,
            "name": self.name,
            "language": self.language,
            "region": self.region,
            "rtl": self.rtl,
        }
        
        if self.currency:
            result["currency"] = {
                "code": self.currency.code,
                "symbol": self.currency.symbol,
                "decimal_separator": self.currency.decimal_separator,
                "thousands_separator": self.currency.thousands_separator,
                "symbol_position": self.currency.symbol_position,
                "format": self.currency.format,
            }
        
        if self.date:
            result["date"] = {
                "formats": self.date.formats,
            }
        
        if self.patterns:
            result["patterns"] = {
                "total_keywords": self.patterns.total_keywords,
                "discount_keywords": self.patterns.discount_keywords,
                "noise_keywords": self.patterns.noise_keywords,
            }
        
        if self.extractors:
            result["extractors"] = {
                "store_detection": self.extractors.store_detection,
                "total_detection": self.extractors.total_detection,
            }
        
        return result
