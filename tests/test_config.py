"""Проверки настроек, от которых зависит безопасность стенда."""

from __future__ import annotations

import dataclasses

import pytest

from app.config import Settings, settings as real_settings


def _with(**changes: object) -> Settings:
    return dataclasses.replace(real_settings, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["development", "demo", "production"])
def test_known_environments_are_accepted(value: str) -> None:
    assert _with(app_env=value, dispatcher_api_key="real-secret-key").app_env == value


def test_unknown_environment_fails_loudly() -> None:
    """Опечатка не должна молча снимать запрет демо-ключа.

    Проверка идёт по списку, а не по сравнению с «production». Иначе
    «prodution» в переменной окружения выглядел бы как рабочая конфигурация,
    а на деле означал бы стенд с ключом «123», открытый наружу.
    """

    with pytest.raises(ValueError, match="APP_ENV"):
        _with(app_env="prodution", dispatcher_api_key="real-secret-key")


def test_production_still_refuses_the_demo_key() -> None:
    """Смысл всей проверки: боевой контур не стартует с ключом «123»."""

    with pytest.raises(ValueError, match="DISPATCHER_API_KEY"):
        _with(app_env="production", dispatcher_api_key="123")


def test_demo_environment_allows_the_demo_key() -> None:
    """Публичная витрина — единственное место, где «123» уместен.

    Логины и пароль демо-ролей там и так напечатаны на экране входа, а ключ,
    который невозможно набрать руками, останавливает показ ровно там, где он
    должен начинаться.
    """

    assert _with(app_env="demo", dispatcher_api_key="123").dispatcher_api_key == "123"
