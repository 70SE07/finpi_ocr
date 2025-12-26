"""
Централизованный реестр локалей.

Автоматически сканирует директорию locales/ и регистрирует все доступные локали.
Предоставляет методы для получения списка локалей и их метаданных.
"""

from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger

from .locale_config_loader import LocaleConfigLoader
from .locale_config import LocaleConfig


class LocaleRegistry:
    """
    Реестр всех доступных локалей.
    
    Автоматически сканирует директорию locales/ и загружает все конфигурации.
    Кэширует загруженные конфигурации для быстрого доступа.
    """
    
    _instance: Optional['LocaleRegistry'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        """Singleton паттерн для единственного реестра."""
        if cls._instance is None:
            cls._instance = super(LocaleRegistry, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Инициализация реестра.
        
        Args:
            locales_dir: Директория с конфигами (по умолчанию locales/ в src/parsing/)
        """
        # Защита от повторной инициализации (singleton)
        if LocaleRegistry._initialized:
            return
        
        if locales_dir is None:
            self.locales_dir = Path(__file__).parent
        else:
            self.locales_dir = Path(locales_dir)
        
        self.config_loader = LocaleConfigLoader(locales_dir)
        
        # Кэш загруженных конфигураций
        self._configs: Dict[str, LocaleConfig] = {}
        self._metadata: Dict[str, Dict] = {}
        
        # Регистрация при инициализации
        self._register_all()
        
        LocaleRegistry._initialized = True
        logger.info(f"[LocaleRegistry] Реестр локалей инициализирован: {len(self._configs)} локалей")
    
    def _register_all(self):
        """
        Сканирует директорию и регистрирует все локали.
        
        Загружает все конфигурации в кэш.
        """
        if not self.locales_dir.exists():
            logger.warning(f"[LocaleRegistry] Директория локалей не найдена: {self.locales_dir}")
            return
        
        for item in self.locales_dir.iterdir():
            # Пропускаем __pycache__ и файлы
            if item.name.startswith("_") or not item.is_dir():
                continue
            
            # Проверяем наличие config.yaml
            if not (item / "config.yaml").exists():
                logger.debug(f"[LocaleRegistry] Пропускаем {item.name}: нет config.yaml")
                continue
            
            locale_code = item.name
            
            try:
                # Загружаем конфигурацию
                config = self.config_loader.load(locale_code)
                
                # Сохраняем в кэш
                self._configs[locale_code] = config
                
                # Сохраняем метаданные
                self._metadata[locale_code] = {
                    "code": config.code,
                    "name": config.name,
                    "language": config.language,
                    "region": config.region,
                    "currency_code": config.currency.code if config.currency else None,
                    "currency_symbol": config.currency.symbol if config.currency else None,
                }
                
                logger.debug(f"[LocaleRegistry] Зарегистрирована локаль: {locale_code} - {config.name}")
                
            except Exception as e:
                logger.error(f"[LocaleRegistry] Ошибка загрузки локали {locale_code}: {e}")
                continue
        
        if not self._configs:
            logger.warning(
                f"[LocaleRegistry] Не найдено ни одной конфигурации локали в {self.locales_dir}"
            )
    
    def get_available_locales(self) -> List[str]:
        """
        Возвращает список кодов доступных локалей.
        
        Returns:
            List[str]: Список кодов локалей (de_DE, pl_PL, ...)
        """
        return sorted(self._configs.keys())
    
    def get_locale_config(self, locale_code: str) -> LocaleConfig:
        """
        Возвращает конфигурацию локали из кэша.
        
        Args:
            locale_code: Код локали (de_DE, pl_PL, ...)
            
        Returns:
            LocaleConfig: Конфигурация локали
            
        Raises:
            ValueError: Если локаль не зарегистрирована
        """
        if locale_code not in self._configs:
            available = self.get_available_locales()
            raise ValueError(
                f"Локаль '{locale_code}' не зарегистрирована.\n"
                f"Доступные локали: {available}\n"
                f"Создайте конфигурацию в {self.locales_dir / locale_code / 'config.yaml'}"
            )
        
        return self._configs[locale_code]
    
    def get_locale_metadata(self, locale_code: str) -> Dict:
        """
        Возвращает метаданные локали.
        
        Args:
            locale_code: Код локали (de_DE, pl_PL, ...)
            
        Returns:
            Dict: Метаданные локали (code, name, language, region, currency)
            
        Raises:
            ValueError: Если локаль не зарегистрирована
        """
        if locale_code not in self._metadata:
            available = self.get_available_locales()
            raise ValueError(
                f"Локаль '{locale_code}' не зарегистрирована.\n"
                f"Доступные локали: {available}"
            )
        
        return self._metadata[locale_code]
    
    def get_all_metadata(self) -> Dict[str, Dict]:
        """
        Возвращает метаданные всех зарегистрированных локалей.
        
        Returns:
            Dict[str, Dict]: Словарь {locale_code: metadata}
        """
        return self._metadata.copy()
    
    def get_locales_by_currency(self, currency_code: str) -> List[str]:
        """
        Возвращает список локалей, использующих указанную валюту.
        
        Args:
            currency_code: Код валюты (EUR, USD, PLN, ...)
            
        Returns:
            List[str]: Список кодов локалей
        """
        locales = []
        for locale_code, metadata in self._metadata.items():
            if metadata.get("currency_code") == currency_code:
                locales.append(locale_code)
        
        return sorted(locales)
    
    def get_locales_by_language(self, language_code: str) -> List[str]:
        """
        Возвращает список локалей на указанном языке.
        
        Args:
            language_code: Код языка (de, en, pl, ...)
            
        Returns:
            List[str]: Список кодов локалей
        """
        locales = []
        for locale_code, metadata in self._metadata.items():
            if metadata.get("language") == language_code:
                locales.append(locale_code)
        
        return sorted(locales)
    
    def is_locale_available(self, locale_code: str) -> bool:
        """
        Проверяет доступность локали.
        
        Args:
            locale_code: Код локали
            
        Returns:
            bool: True если локаль доступна
        """
        return locale_code in self._configs
    
    def get_registry_info(self) -> Dict:
        """
        Возвращает информацию о реестре.
        
        Returns:
            Dict: Информация о зарегистрированных локалях
        """
        # Статистика по валютам
        currencies = {}
        for metadata in self._metadata.values():
            currency = metadata.get("currency_code", "N/A")
            currencies[currency] = currencies.get(currency, 0) + 1
        
        # Статистика по языкам
        languages = {}
        for metadata in self._metadata.values():
            lang = metadata.get("language", "N/A")
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "total_locales": len(self._configs),
            "locales_dir": str(self.locales_dir),
            "available_locales": self.get_available_locales(),
            "currencies": currencies,
            "languages": languages,
        }
    
    @classmethod
    def reset(cls):
        """Сброс singleton (для тестов)."""
        cls._instance = None
        cls._initialized = False

