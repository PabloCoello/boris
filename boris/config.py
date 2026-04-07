"""Configuration loader: .env (secrets) + config.yaml (behavior)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class AssistantConfig:
    name: str = "Boris"
    language: str = "es"
    wake_word: str = "boris"


@dataclass
class STTConfig:
    model: str = "large-v3"
    language: str = "es"
    device: str = "cuda"


@dataclass
class TTSConfig:
    model: str = "xtts_v2"
    language: str = "es"
    speaker_wav: str = "data/audio/reference.wav"


@dataclass
class LLMConfig:
    model: str = "gemma4-26b"
    temperature: float = 0.7
    max_tokens: int = 512


@dataclass
class AudioConfig:
    input_device_name: str | None = None  # None = system default


@dataclass
class MemoryConfig:
    profile_max_tokens: int = 800
    index_max_tokens: int = 400
    data_dir: str = "data/memory"


@dataclass
class SkillHomeConfig:
    enabled: bool = False


@dataclass
class SkillGarminConfig:
    enabled: bool = True


@dataclass
class SkillMusicConfig:
    backend: str = "spotify"


@dataclass
class SkillSearchConfig:
    url: str = "http://localhost:8080"


@dataclass
class SkillsConfig:
    home: SkillHomeConfig = field(default_factory=SkillHomeConfig)
    garmin: SkillGarminConfig = field(default_factory=SkillGarminConfig)
    music: SkillMusicConfig = field(default_factory=SkillMusicConfig)
    search: SkillSearchConfig = field(default_factory=SkillSearchConfig)


@dataclass
class SecretsConfig:
    ollama_host: str = "http://localhost:11434"
    ha_url: str = ""
    ha_token: str = ""
    garmin_email: str = ""
    garmin_password: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    google_credentials_json: str = ""


@dataclass
class Config:
    assistant: AssistantConfig = field(default_factory=AssistantConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    secrets: SecretsConfig = field(default_factory=SecretsConfig)


def _build_dataclass(cls, data: dict):
    """Build a dataclass from a dict, ignoring unknown keys."""
    if data is None:
        return cls()
    valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return cls(**filtered)


def _load_secrets() -> SecretsConfig:
    """Load secrets from environment variables (FIELD_NAME → env FIELD_NAME uppercase)."""
    kwargs = {
        name: os.getenv(name.upper(), f.default)
        for name, f in SecretsConfig.__dataclass_fields__.items()
    }
    return SecretsConfig(**kwargs)


def load_config(config_path: str | Path = "config.yaml", env_path: str | Path = ".env") -> Config:
    """Load configuration from config.yaml and .env files."""
    load_dotenv(env_path)

    yaml_data = {}
    config_file = Path(config_path)
    if config_file.exists():
        yaml_data = yaml.safe_load(config_file.read_text()) or {}

    skills_data = yaml_data.get("skills", {})
    skills = SkillsConfig(
        home=_build_dataclass(SkillHomeConfig, skills_data.get("home")),
        garmin=_build_dataclass(SkillGarminConfig, skills_data.get("garmin")),
        music=_build_dataclass(SkillMusicConfig, skills_data.get("music")),
        search=_build_dataclass(SkillSearchConfig, skills_data.get("search")),
    )

    return Config(
        assistant=_build_dataclass(AssistantConfig, yaml_data.get("assistant")),
        audio=_build_dataclass(AudioConfig, yaml_data.get("audio")),
        stt=_build_dataclass(STTConfig, yaml_data.get("stt")),
        tts=_build_dataclass(TTSConfig, yaml_data.get("tts")),
        llm=_build_dataclass(LLMConfig, yaml_data.get("llm")),
        memory=_build_dataclass(MemoryConfig, yaml_data.get("memory")),
        skills=skills,
        secrets=_load_secrets(),
    )
