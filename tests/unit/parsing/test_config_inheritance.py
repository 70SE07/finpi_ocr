import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open
from src.parsing.locales.config_loader import ConfigLoader, LocaleConfig

# Mock data
MOCK_BASE_YAML = """
common_skip:
  - skip1
  - skip2

weight_patterns:
  - '^\\d+kg'

tax_patterns:
  - '^TAX'
"""

MOCK_LOCALE_YAML = """
locale_code: test_LOC
currency: TEST

skip_keywords:
  - $extends: common_skip
  - local_skip

weight_patterns:
  - $extends: weight_patterns

tax_patterns:
  - local_tax_only
"""

MOCK_BROKEN_EXTENDS_YAML = """
locale_code: test_BROKEN
currency: TEST

skip_keywords:
  - $extends: non_existent_key
"""

@pytest.fixture
def mock_config_files(tmp_path):
    """Creates temporary base.yaml and parsing.yaml for testing."""
    # Setup directories
    locale_dir = tmp_path / "test_LOC"
    locale_dir.mkdir()
    
    # Write base.yaml
    base_file = tmp_path / "base.yaml"
    base_file.write_text(MOCK_BASE_YAML, encoding="utf-8")
    
    # Write parsing.yaml
    parsing_file = locale_dir / "parsing.yaml"
    parsing_file.write_text(MOCK_LOCALE_YAML, encoding="utf-8")
    
    return tmp_path

def test_load_base_config_success(mock_config_files):
    """Test that base config is loaded correctly."""
    config = ConfigLoader._load_base_config(mock_config_files)
    assert "common_skip" in config
    assert "weight_patterns" in config
    assert config["common_skip"] == ["skip1", "skip2"]

def test_resolve_extends_list(mock_config_files):
    """Test resolution of $extends in a list."""
    base_config = ConfigLoader._load_base_config(mock_config_files)
    
    # Case 1: Extend + Local
    input_list = ["$extends: common_skip", "local_item"]
    resolved = ConfigLoader._resolve_extends(input_list, base_config)
    assert resolved == ["skip1", "skip2", "local_item"]
    
    # Case 2: Only Extend
    input_list = ["$extends: weight_patterns"]
    resolved = ConfigLoader._resolve_extends(input_list, base_config)
    assert resolved == ["^\\d+kg"]
    
    # Case 3: No Extend
    input_list = ["pure_local"]
    resolved = ConfigLoader._resolve_extends(input_list, base_config)
    assert resolved == ["pure_local"]

def test_resolve_extends_missing_key(mock_config_files):
    """Test that missing key in base config is handled gracefully."""
    base_config = ConfigLoader._load_base_config(mock_config_files)
    input_list = ["$extends: invalid_key", "local"]
    
    # Should log warning but continue
    resolved = ConfigLoader._resolve_extends(input_list, base_config)
    assert resolved == ["local"]

def test_full_config_loading_inheritance(mock_config_files):
    """Test full integration: loading a locale config with inheritance."""
    # We need to patch the config_dir to point to our temp dir
    # Since ConfigLoader.load uses internal caching and paths, we might need to verify logic via _load_locale_yaml directly if we don't want to mock the recursive calls too deeply or class attributes.
    # However, ConfigLoader._load_locale_yaml is a classmethod that takes config_dir
    
    config = ConfigLoader._load_locale_yaml(mock_config_files, "test_LOC")
    
    # Check Skip Keywords (Inherited + Local)
    assert "skip1" in config.semantic.skip_keywords
    assert "skip2" in config.semantic.skip_keywords
    assert "local_skip" in config.semantic.skip_keywords
    
    # Check Weight Patterns (Inherited only)
    assert "^\\d+kg" in config.semantic.weight_patterns
    
    # Check Tax Patterns (Local only, no extends used in yaml)
    assert "local_tax_only" in config.semantic.tax_patterns
    assert "^TAX" not in config.semantic.tax_patterns 
