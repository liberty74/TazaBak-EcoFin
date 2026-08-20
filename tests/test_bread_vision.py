"""Как выбирается движок разбора фотографии и что он возвращает."""

from __future__ import annotations

import json
from pathlib import Path

import dataclasses

import pytest

from app.config import settings as real_settings
from app.services import bread_vision, gemini_vision
from app.services.clip_bread import BreadClassification, ClipAnalysisError


def _settings_with_key(monkeypatch, key: str) -> None:
    """Settings — замороженный dataclass, поле в нём не подменить.

    Поэтому подменяется весь объект: копия настроек с другим ключом.
    """

    monkeypatch.setattr(
        gemini_vision,
        "settings",
        dataclasses.replace(real_settings, gemini_api_key=key),
    )


class _Response:
    """Минимальный дублёр ответа requests."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def _gemini_answer(numbers: dict[str, float]) -> dict[str, object]:
    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(numbers)}]}}
        ]
    }


@pytest.fixture
def photo(tmp_path: Path) -> Path:
    path = tmp_path / "bread.jpg"
    path.write_bytes(b"not a real jpeg, the transport is stubbed")
    return path


def test_remote_numbers_become_a_distribution(monkeypatch, photo: Path) -> None:
    """Языковая модель может вернуть числа, не дающие в сумме единицу.

    Пересчёт сохраняет порядок, который она имела в виду, но на экране цифры
    складываются — иначе читающий видит проценты, дающие 115%.
    """

    _settings_with_key(monkeypatch, "test-key")
    monkeypatch.setattr(
        gemini_vision.requests,
        "post",
        lambda *a, **k: _Response(
            _gemini_answer({"fresh_bread": 0.9, "moldy_bread": 0.2, "no_bread": 0.05})
        ),
    )

    result = gemini_vision.classify_bread_remote(photo)

    assert result.decision == "fresh_bread"
    assert result.engine == "gemini-vision"
    assert sum(result.probabilities.values()) == pytest.approx(1.0, abs=0.001)
    # Порядок не переставлен пересчётом.
    assert result.probabilities["fresh_bread"] > result.probabilities["moldy_bread"]
    assert result.probabilities["moldy_bread"] > result.probabilities["no_bread"]


def test_remote_refuses_all_zero_answer(monkeypatch, photo: Path) -> None:
    """Три нуля — не распределение, и выдавать по ним вердикт нельзя."""

    _settings_with_key(monkeypatch, "test-key")
    monkeypatch.setattr(
        gemini_vision.requests,
        "post",
        lambda *a, **k: _Response(
            _gemini_answer({"fresh_bread": 0.0, "moldy_bread": 0.0, "no_bread": 0.0})
        ),
    )

    with pytest.raises(ClipAnalysisError):
        gemini_vision.classify_bread_remote(photo)


def test_local_engine_wins_when_installed(monkeypatch, photo: Path) -> None:
    """Там, где CLIP есть, в сеть не ходят: стенд обязан работать без Wi-Fi."""

    local = BreadClassification(
        decision="fresh_bread",
        confidence=0.91,
        probabilities={"fresh_bread": 0.91, "moldy_bread": 0.05, "no_bread": 0.04},
        model="openai/clip-vit-base-patch32",
    )
    monkeypatch.setattr(bread_vision, "local_models_installed", lambda: True)
    monkeypatch.setattr(bread_vision, "classify_bread", lambda path: local)
    monkeypatch.setattr(
        bread_vision,
        "classify_bread_remote",
        lambda path: pytest.fail("удалённый движок не должен вызываться"),
    )

    assert bread_vision.classify(photo) is local


def test_remote_takes_over_without_local_models(monkeypatch, photo: Path) -> None:
    """Без torch кнопка не должна отвечать 503, если настроен удалённый движок."""

    remote = BreadClassification(
        decision="moldy_bread",
        confidence=0.77,
        probabilities={"fresh_bread": 0.13, "moldy_bread": 0.77, "no_bread": 0.10},
        model="gemini-3.1-flash-lite",
        engine="gemini-vision",
    )
    monkeypatch.setattr(bread_vision, "local_models_installed", lambda: False)
    monkeypatch.setattr(bread_vision, "remote_analysis_available", lambda: True)
    monkeypatch.setattr(bread_vision, "classify_bread_remote", lambda path: remote)

    assert bread_vision.classify(photo) is remote


def test_nothing_available_still_raises(monkeypatch, photo: Path) -> None:
    """Ни моделей, ни ключа — честный отказ, а не выдуманный вердикт."""

    monkeypatch.setattr(bread_vision, "local_models_installed", lambda: False)
    monkeypatch.setattr(bread_vision, "remote_analysis_available", lambda: False)

    with pytest.raises(ClipAnalysisError):
        bread_vision.classify(photo)
