"""
DTO контракт: D3 (Categorization) -> Orchestrator

Финальный результат парсинга и категоризации чека.
Это output всей системы, готовый для передачи внешним сервисам.

ВАЖНО: Структура 1 в 1 соответствует ParseResultDTO из finpi_parser_photo.

ВАЛИДАЦИЯ: Pydantic гарантирует корректность данных.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReceiptItem(BaseModel):
    """
    Позиция чека с полной категоризацией.
    """

    name: str = Field(..., description="Название товара/услуги")
    quantity: float | None = Field(None, description="Количество")
    price: float | None = Field(None, description="Цена за единицу")
    total: float | None = Field(None, description="Итоговая стоимость позиции")

    # 5-уровневая категоризация
    product_type: str = Field(..., description="L1: GOODS или SERVICE")
    product_category: str = Field(..., description="L2: Основная категория (например, GROCERIES)")
    product_subcategory_l1: str = Field(..., description="L3: Товарная группа (например, CHEESE)")
    product_subcategory_l2: str | None = Field(None, description="L4: Тип продукта (например, EMMENTAL)")
    product_subcategory_l3: list[str] | None = Field(
        None, description="L5: Характеристики (например, ['UHT', '3.5_PERCENT_FAT'])"
    )
    needs_manual_review: bool | None = Field(False, description="Флаг необходимости ручной проверки")

    merchant: str | None = Field(None, description="Название магазина для позиции")
    store_address: str | None = Field(None, description="Адрес магазина для позиции")
    date: datetime | None = Field(None, description="Дата для позиции")

    model_config = ConfigDict(frozen=True, from_attributes=True)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("product_type")
    @classmethod
    def validate_product_type(cls, v: str) -> str:
        if v not in ["GOODS", "SERVICE"]:
            raise ValueError(f"Invalid product_type: {v}. Must be GOODS or SERVICE.")
        return v


class ReceiptSums(BaseModel):
    """
    Сводные суммы чека.
    """

    total: float | None = Field(None, description="Итоговая сумма")

    model_config = ConfigDict(frozen=True, from_attributes=True)


class DataValidityInfo(BaseModel):
    """
    Информация о валидности данных чека.
    """

    sum_validation_passed: bool = Field(..., description="Совпадение суммы по чеку и сумме позиций")
    sum_difference: float | None = Field(None, description="Разница между суммой позиций и суммой чека")

    model_config = ConfigDict(frozen=True, from_attributes=True)


class ParseResultDTO(BaseModel):
    """
    DTO для результата парсинга и категоризации чека.
    Финальный output системы, идущий в Orchestrator и внешние сервисы.
    """

    success: bool = Field(..., description="Успешность парсинга")
    items: list[ReceiptItem] = Field(default_factory=list, description="Список позиций")
    sums: ReceiptSums | None = Field(None, description="Сводные суммы чека")
    error: str | None = Field(None, description="Текст ошибки, если success=False")
    receipt_id: str | None = Field(None, description="ID чека для связи с хранилищем")
    data_validity: DataValidityInfo | None = Field(None, description="Информация о валидности данных чека")

    # Поле для обратной совместимости (будет удалено позже)
    total_amount: float | None = Field(None, description="Общая сумма чека (deprecated, используйте sums.total)")

    model_config = ConfigDict(frozen=True, from_attributes=True)
