"""``_resolve_jwks_url`` — derive Supabase JWKS URL from env (audit #26).

The previous implementation hardcoded a project subdomain
(``lzhiqnxfveqttsujebiv.supabase.co``) into the source tree. This pins
the resolver behaviour: explicit ``SUPABASE_JWKS_URL`` wins; otherwise
the URL is derived from ``SUPABASE_URL``; otherwise ``None``.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture(autouse=True)
def _reset_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean env so module-level reads are stable."""
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)


def _resolver():
    # Re-import config so each test reads its env via the same code path
    # the module uses on real boot. The function itself reads ``os.environ``
    # at call time, so we don't need to reload to exercise different envs.
    from getviews_pipeline import config

    importlib.reload(config)
    return config._resolve_jwks_url


def test_explicit_jwks_url_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://override.example/jwks.json")
    monkeypatch.setenv("SUPABASE_URL", "https://other.supabase.co")
    assert _resolver()() == "https://override.example/jwks.json"


def test_derived_from_supabase_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co")
    assert (
        _resolver()()
        == "https://test-project.supabase.co/auth/v1/.well-known/jwks.json"
    )


def test_trailing_slash_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co/")
    # No double slash before the auth path.
    assert (
        _resolver()()
        == "https://test-project.supabase.co/auth/v1/.well-known/jwks.json"
    )


def test_returns_none_when_neither_is_set() -> None:
    assert _resolver()() is None
