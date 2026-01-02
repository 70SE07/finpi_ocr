"""
Stage 8: Validation

ЦКП: Валидация результатов парсинга (checksum).

Input: SemanticResult, MetadataResult
Output: ValidationResult (passed/failed, difference)

Правила валидации (ADR-009, ADR-011):
1. SUM(items.total) должна равняться receipt_total
2. Допустимая погрешность: ±0.05 (округление)
3. При несовпадении — это БАГ системы, не проблема чека
"""

from dataclasses import dataclass
from typing import Optional
from loguru import logger

from ..s6_metadata.stage import MetadataResult
from ..s7_semantic.stage import SemanticResult


# Допустимая погрешность для checksum (ADR-011)
CHECKSUM_TOLERANCE = 0.05


@dataclass
class ValidationResult:
    """
    Результат Stage 8: Validation.
    
    ЦКП: Валидность парсинга.
    """
    passed: bool                                # Валидация пройдена
    items_sum: float                            # Сумма товаров
    discounts_sum: float                        # Сумма скидок
    calculated_total: float                     # Расчётная сумма (items - discounts)
    receipt_total: Optional[float]              # Итог из чека
    difference: float                           # Разница
    tolerance: float = CHECKSUM_TOLERANCE       # Допустимая погрешность
    error_message: Optional[str] = None         # Сообщение об ошибке
    
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "items_sum": self.items_sum,
            "discounts_sum": self.discounts_sum,
            "calculated_total": self.calculated_total,
            "receipt_total": self.receipt_total,
            "difference": self.difference,
            "tolerance": self.tolerance,
            "error_message": self.error_message,
        }


class ValidationStage:
    """
    Stage 8: Validation (Checksum).
    
    ЦКП: Проверка что сумма товаров = итогу чека.
    
    По ADR-009: если валидация не проходит — это БАГ системы.
    По ADR-011: допустима погрешность ±0.05 из-за округления.
    """
    
    def __init__(self, tolerance: float = CHECKSUM_TOLERANCE):
        """
        Args:
            tolerance: Допустимая погрешность (по умолчанию 0.05)
        """
        self.tolerance = tolerance
    
    def process(
        self,
        semantic: SemanticResult,
        metadata: MetadataResult,
    ) -> ValidationResult:
        """
        Валидирует результаты парсинга.
        
        Args:
            semantic: Результат Stage 7
            metadata: Результат Stage 6
            
        Returns:
            ValidationResult: Результат валидации
        """
        logger.debug("[Stage 8: Validation] Проверка checksum")
        
        # Вычисляем суммы
        items_sum = sum(item.total or 0 for item in semantic.items if not item.is_discount)
        discounts_sum = sum(abs(item.total or 0) for item in semantic.discounts)
        
        # Расчётная сумма (товары минус скидки)
        calculated_total = round(items_sum - discounts_sum, 2)
        
        # Итог из чека
        receipt_total = metadata.receipt_total
        
        # Если нет итога из чека — не можем валидировать
        if receipt_total is None:
            logger.warning("[Stage 8: Validation] Нет итога чека для валидации")
            return ValidationResult(
                passed=False,
                items_sum=items_sum,
                discounts_sum=discounts_sum,
                calculated_total=calculated_total,
                receipt_total=None,
                difference=0.0,
                tolerance=self.tolerance,
                error_message="Не удалось извлечь итоговую сумму из чека",
            )
        
        # Вычисляем разницу
        difference = abs(calculated_total - receipt_total)
        
        # Проверяем tolerance
        passed = difference <= self.tolerance
        
        error_message = None
        if not passed:
            error_message = (
                f"Checksum mismatch: calculated={calculated_total}, "
                f"receipt={receipt_total}, diff={difference:.2f} "
                f"(tolerance={self.tolerance})"
            )
            logger.error(f"[Stage 8: Validation] {error_message}")
        else:
            logger.info(
                f"[Stage 8: Validation] PASSED: {calculated_total} ≈ {receipt_total} "
                f"(diff={difference:.2f})"
            )
        
        return ValidationResult(
            passed=passed,
            items_sum=items_sum,
            discounts_sum=discounts_sum,
            calculated_total=calculated_total,
            receipt_total=receipt_total,
            difference=difference,
            tolerance=self.tolerance,
            error_message=error_message,
        )
