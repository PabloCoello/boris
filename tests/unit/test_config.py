"""Tests for boris.config module."""

from __future__ import annotations

from pathlib import Path

from boris.config import Config, load_config


def test_load_config_from_yaml(tmp_config: tuple[Path, Path]):
    config_path, env_path = tmp_config
    cfg = load_config(config_path=config_path, env_path=env_path)

    assert cfg.assistant.name == "TestBoris"
    assert cfg.assistant.wake_word == "test"
    assert cfg.stt.model == "tiny"
    assert cfg.stt.device == "cpu"
    assert cfg.llm.model == "test-model"
    assert cfg.llm.temperature == 0.5
    assert cfg.llm.max_tokens == 256
    assert cfg.memory.data_dir == "/tmp/test_memory"


def test_load_secrets_from_env(tmp_config: tuple[Path, Path]):
    config_path, env_path = tmp_config
    cfg = load_config(config_path=config_path, env_path=env_path)

    assert cfg.secrets.ollama_host == "http://localhost:11434"
    assert cfg.secrets.ha_token == "test-token-123"


def test_defaults_when_no_config(tmp_path: Path):
    missing_config = tmp_path / "missing.yaml"
    missing_env = tmp_path / "missing.env"
    cfg = load_config(config_path=missing_config, env_path=missing_env)

    assert cfg.assistant.name == "Boris"
    assert cfg.llm.model == "gemma4-26b"
    assert cfg.stt.model == "large-v3"
    assert cfg.skills.home.enabled is False
    assert cfg.skills.music.backend == "spotify"


def test_skills_config(tmp_config: tuple[Path, Path]):
    config_path, env_path = tmp_config
    cfg = load_config(config_path=config_path, env_path=env_path)

    # Skills not specified in test config → defaults
    assert cfg.skills.home.enabled is False
    assert cfg.skills.garmin.enabled is True
    assert cfg.skills.music.backend == "spotify"
    assert cfg.skills.search.url == "http://localhost:8080"


def test_config_is_dataclass():
    cfg = Config()
    assert hasattr(cfg, "assistant")
    assert hasattr(cfg, "secrets")
    assert hasattr(cfg, "skills")
