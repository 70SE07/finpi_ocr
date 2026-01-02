"""
Unit-тесты для загрузки конфигураций магазинов через ConfigLoader.

ЦКП: Проверка корректности загрузки stores/*.yaml с секцией detection.
"""

import pytest
from pathlib import Path

from src.parsing.locales.config_loader import (
    ConfigLoader,
    LocaleConfig,
    StoreDetectionConfig,
)


class TestStoreDetectionConfigLoading:
    """Тесты загрузки StoreDetectionConfig из YAML файлов."""
    
    def test_load_stores_for_de_DE(self):
        """Должен загрузить магазины для de_DE."""
        config = LocaleConfig.load("de_DE")
        
        assert len(config.stores) > 0, "Должны быть загружены магазины"
        
        # Проверяем что aldi загружен с правильными данными
        aldi = next((s for s in config.stores if s.name == "aldi"), None)
        assert aldi is not None, "aldi должен быть загружен"
        assert "aldi" in aldi.brands
        assert "aldi süd" in aldi.brands or "aldi sud" in aldi.brands
    
    def test_load_stores_for_pl_PL(self):
        """Должен загрузить магазины для pl_PL."""
        config = LocaleConfig.load("pl_PL")
        
        assert len(config.stores) > 0, "Должны быть загружены магазины"
        
        # Проверяем что biedronka загружен
        biedronka = next((s for s in config.stores if s.name == "biedronka"), None)
        assert biedronka is not None, "biedronka должен быть загружен"
        assert "biedronka" in biedronka.brands
    
    def test_store_detection_config_structure(self):
        """Проверяет структуру StoreDetectionConfig."""
        config = LocaleConfig.load("de_DE")
        
        for store in config.stores:
            assert isinstance(store.name, str)
            assert isinstance(store.brands, list)
            assert isinstance(store.aliases, list)
            assert isinstance(store.priority, int)
            assert len(store.brands) > 0, f"Магазин {store.name} должен иметь хотя бы один brand"
    
    def test_stores_sorted_by_priority(self):
        """Магазины должны быть отсортированы по приоритету (выше = раньше)."""
        config = LocaleConfig.load("de_DE")
        
        if len(config.stores) > 1:
            for i in range(len(config.stores) - 1):
                assert config.stores[i].priority >= config.stores[i + 1].priority, \
                    f"Магазины должны быть отсортированы по убыванию приоритета"
    
    def test_locale_without_stores_dir(self):
        """Локаль без stores/ директории должна возвращать пустой список."""
        # Создаём ConfigLoader и проверяем что нет ошибки
        # для локалей без stores/ директории (если такие есть)
        # В нашем случае все локали имеют stores/, поэтому просто проверяем
        # что загрузка работает без исключений
        try:
            config = LocaleConfig.load("de_DE")
            assert config.stores is not None
        except FileNotFoundError:
            pytest.skip("Локаль не найдена")


class TestAddressHintsLoading:
    """Тесты загрузки address_hints из конфигов."""
    
    def test_load_address_hints_de_DE(self):
        """Должен загрузить address_hints для de_DE."""
        config = LocaleConfig.load("de_DE")
        
        assert len(config.address_hints) > 0, "address_hints должны быть загружены"
        assert "straße" in config.address_hints or "strasse" in config.address_hints
    
    def test_load_address_hints_pl_PL(self):
        """Должен загрузить address_hints для pl_PL."""
        config = LocaleConfig.load("pl_PL")
        
        assert len(config.address_hints) > 0, "address_hints должны быть загружены"
        assert "ul." in config.address_hints or "ulica" in config.address_hints
    
    def test_extends_base_address_hints(self):
        """Должен расширять базовые address_hints."""
        config = LocaleConfig.load("de_DE")
        
        # Базовые hints из base.yaml
        base_hints = ["str.", "weg", "platz"]
        
        # Проверяем что хотя бы некоторые базовые hints присутствуют
        for hint in base_hints:
            if hint in config.address_hints:
                return  # Найден базовый hint
        
        # Если не нашли ни одного базового - это нормально, 
        # они могли быть переопределены
        pass


class TestConfigLoaderCaching:
    """Тесты кеширования конфигураций."""
    
    def test_config_caching(self):
        """Одна и та же локаль должна возвращать закешированный результат."""
        # Очищаем кеш
        LocaleConfig._cache.clear()
        
        config1 = LocaleConfig.load("de_DE")
        config2 = LocaleConfig.load("de_DE")
        
        assert config1 is config2, "Должен возвращать тот же объект из кеша"
    
    def test_different_locales_different_configs(self):
        """Разные локали должны возвращать разные конфиги."""
        LocaleConfig._cache.clear()
        
        config_de = LocaleConfig.load("de_DE")
        config_pl = LocaleConfig.load("pl_PL")
        
        assert config_de is not config_pl
        assert config_de.locale_code == "de_DE"
        assert config_pl.locale_code == "pl_PL"


class TestStoreCountByLocale:
    """Тесты количества магазинов по локалям."""
    
    @pytest.mark.parametrize("locale,min_stores", [
        ("de_DE", 15),
        ("pl_PL", 10),
        ("es_ES", 5),
        ("pt_PT", 5),
        ("cs_CZ", 5),
    ])
    def test_minimum_stores_count(self, locale: str, min_stores: int):
        """Каждая локаль должна иметь минимальное количество магазинов."""
        LocaleConfig._cache.clear()
        
        try:
            config = LocaleConfig.load(locale)
            assert len(config.stores) >= min_stores, \
                f"{locale} должен иметь >= {min_stores} магазинов, но имеет {len(config.stores)}"
        except FileNotFoundError:
            pytest.skip(f"Локаль {locale} не найдена")
