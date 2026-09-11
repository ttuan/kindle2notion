import pytest
from click import UsageError
from decouple import UndefinedValueError

from kindle2notion import __main__
from kindle2notion.__main__ import _resolve


@pytest.fixture
def env(monkeypatch):
    """Replace decouple's config so the tests never read the real .env file."""
    values = {}

    def fake_config(name):
        if name not in values:
            raise UndefinedValueError(name)
        return values[name]

    monkeypatch.setattr(__main__, "config", fake_config)
    return values


def test_resolve_prefers_the_explicit_argument(env):
    env["NOTION_TOKEN"] = "from-env"

    assert _resolve("from-argument", "NOTION_TOKEN", "Notion token") == "from-argument"


def test_resolve_falls_back_to_the_environment_when_the_argument_is_omitted(env):
    env["NOTION_TOKEN"] = "from-env"

    assert _resolve(None, "NOTION_TOKEN", "Notion token") == "from-env"


def test_resolve_raises_a_usage_error_when_nothing_provides_the_value(env):
    with pytest.raises(UsageError, match="NOTION_TOKEN"):
        _resolve(None, "NOTION_TOKEN", "Notion token")
