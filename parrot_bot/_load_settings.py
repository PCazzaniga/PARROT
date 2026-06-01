"""
Module for loading and saving settings data.

Attributes:
    settings:   Settings object

Functions:
    save_settings():    Saves settings back in the settings file

Exceptions:
    SettingsSaveError:  Raised on errors when saving settings
"""

from pathlib import Path
from pydantic import BaseModel, Field, ValidationInfo, field_validator

class SettingsSaveError(Exception):
    pass

class Pattern(BaseModel):
    MATCH: str
    SAY: str

class SpecialCases(BaseModel):
    RECURSIVE: str
    PATTERNS: list[Pattern]

class Config(BaseModel):
    #'...' makes the field required (otherwise they can be missing and default to their type's defaul value)
    REPLACEMENT_WORD: str = Field(..., min_length=1)
    INTENSITY: float = Field(..., ge=1, le=100)
    WAIT_SECONDS: int = Field(..., ge=30)
    WAIT_MESSAGES: int = Field(..., ge=5)
    NOTARGET_MODE: bool = Field(...)
    VIP_IDS: list[int]  # lists don't have a default value so these are automatically required
    IGNORED_IDS: list[int]
    SPECIAL_CASES: SpecialCases
    ADVANCED_MODE: bool = Field(...)
    MAX_TARGET_LENGTH: int = Field(..., ge=30)

    @field_validator("VIP_IDS", "IGNORED_IDS")
    @classmethod
    def ids_must_be_positive(cls, values: list[int], info: ValidationInfo) -> list[int]:
        invalid_values = [v for v in values if v < 0]
        if invalid_values:
            raise ValueError(f"Invalid IDs detected in {info.field_name}: {invalid_values}")
        return values

SETTINGS_FILE = Path(__file__).parent / "bot_settings.json"

try:
    with open(SETTINGS_FILE, encoding='utf-8') as settings_file:
        settings = Config.model_validate_json(settings_file.read())
except FileNotFoundError:
    raise FileNotFoundError(f"Settings file '{SETTINGS_FILE}' not found.")
except Exception as e:
    raise ValueError(f"Failed to load settings with error: {e}")

def save_settings() -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding='utf-8') as settings_file:
            settings_file.write(settings.model_dump_json(indent=2))
    except OSError as e:
        raise SettingsSaveError(f"Failed to save settings to '{SETTINGS_FILE}' with error: {e}")