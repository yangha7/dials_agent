"""
Tests for per-provider max_tokens resolution in config.py.

Regression coverage for a real gap found live: max_tokens was a single
global default (16384) shared across all four providers, but they don't
share the same real ceiling -- GPT-4o's actual output-token limit IS 16384
(raising it further just errors), while Claude Sonnet 4/4.5 (what
"cborg"/"anthropic" resolve to here) support up to 64K on the standard
synchronous API. A long, context-heavy turn hit the old shared 16384 limit
mid-generation and silently produced nothing (see cli.py's
_warn_if_response_truncated, added in v2.7.3).

Note: Settings() reads from the real environment/.env for any field not
explicitly passed, so every test here blanks all four provider API keys
explicitly and sets llm_provider directly -- otherwise a real API key
sitting in a developer's actual .env (e.g. a live CBORG_API_KEY) silently
wins provider auto-detection regardless of what the test intended.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.config import Settings, DEFAULT_MAX_TOKENS


def make_settings(provider: str, **overrides) -> Settings:
    kwargs = {
        "llm_provider": provider,
        "cborg_api_key": "", "anthropic_api_key": "", "openai_api_key": "", "gemini_api_key": "",
    }
    kwargs[f"{provider}_api_key"] = "dummy"
    kwargs.update(overrides)
    return Settings(**kwargs)


class TestResolvedMaxTokens:
    def test_cborg_defaults_to_64000(self):
        assert make_settings("cborg").get_resolved_max_tokens() == 64000

    def test_anthropic_defaults_to_64000(self):
        assert make_settings("anthropic").get_resolved_max_tokens() == 64000

    def test_openai_stays_at_its_real_ceiling_16384(self):
        # GPT-4o's actual output-token limit -- must NOT be raised to match
        # Claude's higher ceiling, that would just cause API errors.
        assert make_settings("openai").get_resolved_max_tokens() == 16384

    def test_gemini_stays_conservative_16384(self):
        assert make_settings("gemini").get_resolved_max_tokens() == 16384

    def test_explicit_max_tokens_overrides_the_provider_default(self):
        s = make_settings("cborg", max_tokens=8000)
        assert s.get_resolved_max_tokens() == 8000

    def test_unset_max_tokens_field_defaults_to_zero_sentinel(self):
        # 0 means "use the provider default" -- confirms the sentinel itself,
        # not just the resolved value, so a future refactor can't silently
        # reintroduce a single shared hardcoded default on the field itself.
        assert make_settings("cborg").max_tokens == 0

    def test_default_max_tokens_dict_has_all_four_providers(self):
        assert set(DEFAULT_MAX_TOKENS.keys()) == {"cborg", "anthropic", "openai", "gemini"}
