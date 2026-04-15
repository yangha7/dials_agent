"""
Configuration settings for the DIALS AI Agent.

Supports multiple LLM providers with auto-detection:
  - CBORG (LBL users) via CBORG_API_KEY
  - OpenAI via OPENAI_API_KEY
  - Google Gemini via GEMINI_API_KEY
  - Anthropic Claude (direct) via ANTHROPIC_API_KEY
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


# Default models per provider
DEFAULT_MODELS = {
    "cborg": "anthropic/claude-sonnet",
    "openai": "gpt-4o",
    "gemini": "gemini-2.5-pro",
    "anthropic": "claude-sonnet-4-20250514",
}

# Default base URLs per provider
DEFAULT_BASE_URLS = {
    "cborg": "https://api.cborg.lbl.gov",
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ── LLM Provider settings ──────────────────────────────────────────
    # Explicit provider selection (auto-detected if not set)
    llm_provider: str = Field(
        default="",
        description="LLM provider: 'cborg', 'openai', 'gemini', 'anthropic' (auto-detected from API keys if empty)"
    )
    
    # Backward compatibility: api_provider maps to llm_provider
    api_provider: str = Field(
        default="",
        description="(Deprecated) Use LLM_PROVIDER instead. Kept for backward compatibility."
    )
    
    # API keys for each provider
    cborg_api_key: str = Field(
        default="",
        description="CBORG API key (LBL users)"
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude (direct API)"
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key"
    )
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key"
    )
    
    # LLM configuration overrides
    llm_base_url: str = Field(
        default="",
        description="Override the API base URL for the chosen provider"
    )
    # Backward compatibility
    openai_base_url: str = Field(
        default="",
        description="(Deprecated) Use LLM_BASE_URL instead."
    )
    
    model: str = Field(
        default="",
        description="Model to use (auto-selected per provider if empty)"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens in response"
    )
    
    # ── DIALS settings ─────────────────────────────────────────────────
    dials_path: str = Field(
        default="",
        description="Path to DIALS installation bin directory (empty for system PATH)"
    )
    working_directory: str = Field(
        default=".",
        description="Default working directory for DIALS output files"
    )
    data_directory: str = Field(
        default="",
        description="Directory containing input data files (images, HDF5, etc.)"
    )
    command_timeout: int = Field(
        default=3600,
        description="Timeout for DIALS commands in seconds (default: 1 hour)"
    )
    
    # ── Web server settings ────────────────────────────────────────────
    host: str = Field(
        default="127.0.0.1",
        description="Host for web server"
    )
    port: int = Field(
        default=8000,
        description="Port for web server"
    )
    
    # ── Logging settings ───────────────────────────────────────────────
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
    
    def get_resolved_provider(self) -> str:
        """
        Resolve the LLM provider, with auto-detection from API keys.
        
        Priority:
        1. Explicit LLM_PROVIDER setting
        2. Backward-compatible API_PROVIDER setting
        3. Auto-detect from whichever API key is set (CBORG first)
        """
        # Explicit provider
        if self.llm_provider:
            return self.llm_provider.lower()
        
        # Backward compatibility with API_PROVIDER
        if self.api_provider:
            provider = self.api_provider.lower()
            # Map old "openai" provider to "cborg" if using CBORG URL
            if provider == "openai" and "cborg" in self.openai_base_url.lower():
                return "cborg"
            return provider
        
        # Auto-detect from API keys
        if self.cborg_api_key:
            return "cborg"
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "anthropic"
        
        return "anthropic"  # Default fallback
    
    def get_resolved_api_key(self) -> str:
        """Get the API key for the resolved provider."""
        provider = self.get_resolved_provider()
        if provider == "cborg":
            return self.cborg_api_key or self.openai_api_key
        elif provider == "openai":
            return self.openai_api_key
        elif provider == "gemini":
            return self.gemini_api_key
        elif provider == "anthropic":
            return self.anthropic_api_key
        return ""
    
    def get_resolved_base_url(self) -> str:
        """Get the base URL for the resolved provider."""
        # Explicit override takes priority
        if self.llm_base_url:
            return self.llm_base_url
        # Backward compatibility
        if self.openai_base_url:
            return self.openai_base_url
        # Default per provider
        provider = self.get_resolved_provider()
        return DEFAULT_BASE_URLS.get(provider, "")
    
    def get_resolved_model(self) -> str:
        """Get the model for the resolved provider."""
        if self.model:
            return self.model
        provider = self.get_resolved_provider()
        return DEFAULT_MODELS.get(provider, "claude-sonnet-4-20250514")
    
    def get_api_type(self) -> str:
        """
        Get the API type (how to call the API).
        
        Returns 'openai' for OpenAI-compatible APIs (CBORG, OpenAI, Gemini)
        or 'anthropic' for native Anthropic API.
        """
        provider = self.get_resolved_provider()
        if provider in ("cborg", "openai", "gemini"):
            return "openai"  # All use OpenAI-compatible API format
        return "anthropic"
    
    def get_dials_command(self, command: str) -> str:
        """Get the full path to a DIALS command."""
        if self.dials_path:
            return str(Path(self.dials_path) / command)
        return command
    
    def validate_api_key(self) -> bool:
        """Check if API key is configured for the resolved provider."""
        return bool(self.get_resolved_api_key())
    
    def get_api_key(self) -> str:
        """Get the API key for the resolved provider."""
        return self.get_resolved_api_key()
    
    def get_provider_display_name(self) -> str:
        """Get a human-readable name for the resolved provider."""
        names = {
            "cborg": "CBORG (Claude at Berkeley)",
            "openai": "OpenAI",
            "gemini": "Google Gemini",
            "anthropic": "Anthropic Claude (direct)",
        }
        return names.get(self.get_resolved_provider(), self.get_resolved_provider())


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
