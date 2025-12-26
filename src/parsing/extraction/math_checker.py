from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

@dataclass
class MathResult:
    is_valid: bool
    difference: Decimal = Decimal(0)
    expected_total: Optional[Decimal] = None

class MathChecker:
    """Элемент-функция: Проверяет математическую корректность (qty * unit_price == total)."""
    
    def verify(self, qty: Optional[Decimal], unit_price: Optional[Decimal], total_price: Optional[Decimal]) -> MathResult:
        """
        ЦКП: Результат верификации (MathResult).
        """
        if qty is None or unit_price is None or total_price is None:
            return MathResult(is_valid=False)
            
        expected = (qty * unit_price).quantize(Decimal("0.01"))
        actual = total_price.quantize(Decimal("0.01"))
        
        diff = abs(expected - actual)
        
        # Погрешность в 0.01 допустима (округление)
        return MathResult(
            is_valid=(diff <= Decimal("0.01")),
            difference=diff,
            expected_total=expected
        )


