"""
Strategy Factory - фабрика для выбора подходящей стратегии.

На основе контекста (shop name) выбирает правильную стратегию.
"""

from typing import Dict, Optional
from loguru import logger

from .base import AbstractStrategy
from .default import DefaultStrategy
from .rewe import ReweStrategy
from .aldi import AldiStrategy
from .dm import DMStrategy
from .edeka import EdekaStrategy


class StrategyFactory:
    """
    Фабрика для выбора стратегии на основе контекста.
    
    Пример:
        factory = StrategyFactory()
        strategy = factory.get("Rewe")
        plan = strategy.decide(metrics)
    """
    
    # Маппинг магазинов на стратегии
    STRATEGY_MAP: Dict[str, AbstractStrategy] = {
        "rewe": ReweStrategy(),
        "aldi": AldiStrategy(),
        "dm": DMStrategy(),
        "edeka": EdekaStrategy(),
    }
    
    def get(self, shop_name: Optional[str] = None) -> AbstractStrategy:
        """
        Получить стратегию для магазина.
        
        Args:
            shop_name: Название магазина (нормализуется к нижнему регистру)
                      Если None или неизвестное название → DefaultStrategy
                      
        Returns:
            AbstractStrategy для этого магазина
        """
        if not shop_name:
            logger.debug("[StrategyFactory] shop_name не задан → используем Default")
            return DefaultStrategy()
        
        # Нормализуем название (нижний регистр, trim)
        normalized_name = shop_name.strip().lower()
        
        if normalized_name in self.STRATEGY_MAP:
            strategy = self.STRATEGY_MAP[normalized_name]
            logger.debug(f"[StrategyFactory] Выбрана стратегия: {strategy.name}")
            return strategy
        else:
            logger.warning(
                f"[StrategyFactory] Неизвестный магазин '{shop_name}' "
                f"({normalized_name}) → используем Default"
            )
            return DefaultStrategy()
    
    def register(self, shop_name: str, strategy: AbstractStrategy) -> None:
        """
        Зарегистрировать новую стратегию.
        
        Это позволит добавлять стратегии для новых магазинов в runtime.
        
        Args:
            shop_name: Название магазина (нижний регистр)
            strategy: Экземпляр AbstractStrategy
        """
        self.STRATEGY_MAP[shop_name.lower()] = strategy
        logger.info(f"[StrategyFactory] Зарегистрирована новая стратегия: {shop_name}")
