"""
Stage 8: Validation

ЦКП: Валидация checksum (SUM(items) = receipt_total).
"""

from .stage import ValidationStage, ValidationResult

__all__ = ["ValidationStage", "ValidationResult"]
