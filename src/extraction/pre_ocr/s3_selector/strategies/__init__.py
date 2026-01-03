"""
Strategies sub-package для Stage 3 Selector.

Реализует Strategy Pattern для выбора обработки на основе контекста.
"""

from .base import AbstractStrategy
from .default import DefaultStrategy
from .rewe import ReweStrategy
from .aldi import AldiStrategy
from .dm import DMStrategy
from .edeka import EdekaStrategy
from .factory import StrategyFactory

__all__ = [
    "AbstractStrategy",
    "DefaultStrategy",
    "ReweStrategy",
    "AldiStrategy",
    "DMStrategy",
    "EdekaStrategy",
    "StrategyFactory",
]
