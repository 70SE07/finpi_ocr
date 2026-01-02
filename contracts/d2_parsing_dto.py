"""
DTO контракт: D2 (Parsing) -> D3 (Categorization)

Результат парсинга чека до категоризации.
Содержит raw данные извлеченные из чека без продуктовых категорий.

ВАЖНО: Структура 1 в 1 соответствует RawReceiptDTO из finpi_parser_photo.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawReceiptItem(BaseModel):
    """
    Некатегоризированный товар - результат OCR + парсинга, до AI категоризации.
    """

    name: str = Field(..., description="Название товара как извлечено из чека")
    quantity: float | None = Field(None, description="Количество")
    price: float | None = Field(None, description="Цена за единицу")
    total: float | None = Field(None, description="Итоговая цена за позицию")
    date: datetime | None = Field(None, description="Дата товара (если присутствует)")

    model_config = ConfigDict(frozen=True, from_attributes=True)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price", "total")
    @classmethod
    def validate_money_values(cls, v: float | None) -> float | None:
        # Разрешаем отрицательные значения для возвратов/скидок
        return v


class RawReceiptDTO(BaseModel):
    """
    DTO для результатов парсинга чека (до категоризации).

    Это output парсинг-слоя (OCR + извлечение).
    Передается в слой категоризации для добавления продуктовых категорий.
    """

    items: list[RawReceiptItem] = Field(
        default_factory=list, description="Список raw товаров без категорий"
    )
    total_amount: float | None = Field(None, description="Итоговая сумма извлеченная из чека")
    merchant: str | None = Field(None, description="Название магазина/продавца")
    store_address: str | None = Field(None, description="Адрес магазина")
    date: datetime | None = Field(None, description="Дата чека")
    receipt_id: str | None = Field(None, description="Уникальный ID чека")
    ocr_text: str | None = Field(None, description="Raw OCR текст для отладки")
    detected_locale: str | None = Field(None, description="Определенный язык/локаль")
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Метрики парсинга (тайминги, количество токенов)"
    )

    model_config = ConfigDict(frozen=True, from_attributes=True)
