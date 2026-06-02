import pytest

from zomato_ai.config.settings import ConfigError, load_settings, require_llm_settings


def test_load_settings_uses_phase_zero_defaults() -> None:
    settings = load_settings({})

    assert settings.dataset_cache_dir == ".cache/zomato"
    assert settings.max_candidates == 30
    assert settings.top_k_output == 5
    assert settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert settings.llm_timeout_seconds == 20
    assert settings.llm_max_retries == 1
    assert settings.llm_enabled is False


def test_load_settings_enables_llm_only_when_key_and_model_exist() -> None:
    settings = load_settings({"LLM_API_KEY": "secret", "LLM_MODEL": "demo-model"})

    assert settings.llm_enabled is True


def test_require_llm_settings_fails_only_when_llm_feature_needs_it() -> None:
    settings = load_settings({})

    with pytest.raises(ConfigError, match="LLM_API_KEY, LLM_MODEL, and LLM_BASE_URL"):
        require_llm_settings(settings)


def test_load_settings_rejects_invalid_candidate_limit() -> None:
    with pytest.raises(ConfigError, match="MAX_CANDIDATES must be greater than zero"):
        load_settings({"MAX_CANDIDATES": "0"})


def test_load_settings_rejects_top_k_above_candidate_limit() -> None:
    with pytest.raises(ConfigError, match="TOP_K_OUTPUT must be less than or equal"):
        load_settings({"MAX_CANDIDATES": "3", "TOP_K_OUTPUT": "5"})


def test_load_settings_rejects_invalid_log_level() -> None:
    with pytest.raises(ConfigError, match="LOG_LEVEL must be one of"):
        load_settings({"LOG_LEVEL": "LOUD"})


def test_load_settings_reads_local_dotenv_without_overriding_environment(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAX_CANDIDATES", "12")
    monkeypatch.delenv("TOP_K_OUTPUT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    tmp_path.joinpath(".env").write_text(
        "MAX_CANDIDATES=99\nTOP_K_OUTPUT=4\nLOG_LEVEL=debug\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.max_candidates == 12
    assert settings.top_k_output == 4
    assert settings.log_level == "DEBUG"
