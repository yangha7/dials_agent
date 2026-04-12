"""
Configuration settings for the DIALS AI Agent.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Provider settings
    api_provider: str = Field(
        default="anthropic",
        description="API provider: 'anthropic' for native API, 'openai' for OpenAI-compatible (e.g., CBORG)"
    )
    
    # Anthropic API settings (native)
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude (native API)"
    )
    
    # OpenAI-compatible API settings (for CBORG, etc.)
    openai_api_key: str = Field(
        default="",
        description="API key for OpenAI-compatible endpoints (e.g., CBORG)"
    )
    openai_base_url: str = Field(
        default="https://api.cborg.lbl.gov",
        description="Base URL for OpenAI-compatible API (e.g., https://api.cborg.lbl.gov)"
    )
    
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model to use (e.g., claude-sonnet-4-20250514, anthropic/claude-sonnet)"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens in response"
    )
    
    # DIALS settings
    dials_path: str = Field(
        default="",
        description="Path to DIALS installation (empty for system PATH)"
    )
    working_directory: str = Field(
        default=".",
        description="Default working directory for DIALS commands"
    )
    command_timeout: int = Field(
        default=3600,
        description="Timeout for DIALS commands in seconds (default: 1 hour)"
    )
    
    # Web server settings
    host: str = Field(
        default="127.0.0.1",
        description="Host for web server"
    )
    port: int = Field(
        default=8000,
        description="Port for web server"
    )
    
    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path (None for stdout only)"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
    
    def get_dials_command(self, command: str) -> str:
        """Get the full path to a DIALS command."""
        if self.dials_path:
            return str(Path(self.dials_path) / command)
        return command
    
    def validate_api_key(self) -> bool:
        """Check if API key is configured for the selected provider."""
        if self.api_provider == "openai":
            return bool(self.openai_api_key)
        else:
            return bool(self.anthropic_api_key)
    
    def get_api_key(self) -> str:
        """Get the API key for the selected provider."""
        if self.api_provider == "openai":
            return self.openai_api_key
        else:
            return self.anthropic_api_key


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def configure_from_env_file(env_file: str = ".env") -> Settings:
    """Reload settings from a specific env file."""
    global settings
    settings = Settings(_env_file=env_file)
    return settings
