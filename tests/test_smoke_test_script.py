from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_smoke_module():
    path = Path(__file__).resolve().parent.parent / "scripts" / "smoke_test.py"
    spec = importlib.util.spec_from_file_location("alexandria_smoke_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_script_checks_catalog_and_recent_jobs(monkeypatch):
    smoke = _load_smoke_module()

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _fake_get(url, timeout=15):  # type: ignore[no-untyped-def]
        if "/api/prompts" in url:
            return _Response(
                {
                    "prompts": [
                        {
                            "id": "alexandria-wildcard-art-nouveau-poster",
                            "prompt_template": "Book cover illustration — no text, no lettering. Scene: {SCENE}. STYLE: Art Nouveau illustration with graceful figure styling.",
                            "negative_prompt": "no vector art, no airbrushed surfaces, no seamless blending, no uniform color fills, no visible circle outline, no wreath, no sunburst",
                        },
                        {"id": "p2"},
                        {"id": "p3"},
                        {"id": "p4"},
                        {"id": "p5"},
                    ]
                }
            )
        if "/api/jobs" in url:
            return _Response(
                {
                    "jobs": [
                        {
                            "id": "job-12345678",
                            "status": "completed",
                            "created_at": "2026-03-17T12:00:00Z",
                            "result": {
                                "results": [
                                    {
                                        "prompt": (
                                            "Oil paint on stretched linen canvas, visible impasto brushwork throughout — "
                                            "Scene: Emma at Hartfield. STYLE: Romantic Realism. "
                                            "Surface shows natural material texture: visible brushstrokes, pigment variation, paper grain."
                                        ),
                                        "negative_prompt": "no vector art, no airbrushed surfaces, no seamless blending, no uniform color fills, no visible circle outline, no wreath, no sunburst",
                                    }
                                ]
                            },
                        }
                    ]
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(smoke.requests, "get", _fake_get)

    assert smoke.check_prompt_catalog("https://example.test", "classics") == (True, "Prompt catalog: 5 entries")
    jobs_ok, messages = smoke.check_recent_jobs("https://example.test", "classics")
    assert jobs_ok is True
    assert messages == ["Recent completed jobs checked: 1"]


def test_smoke_script_reports_missing_negative_prompt_terms(monkeypatch):
    smoke = _load_smoke_module()

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _fake_get(url, timeout=15):  # type: ignore[no-untyped-def]
        if "/api/jobs" in url:
            return _Response(
                {
                    "jobs": [
                        {
                            "id": "job-deadbeef",
                            "status": "completed",
                            "created_at": "2026-03-17T12:00:00Z",
                            "result": {
                                "results": [
                                    {
                                        "prompt": "Scene: Emma at Hartfield.",
                                        "negative_prompt": "no vector art only",
                                    }
                                ]
                            },
                        }
                    ]
                }
            )
        return _Response({"prompts": [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}, {"id": "p4"}, {"id": "p5"}]})

    monkeypatch.setattr(smoke.requests, "get", _fake_get)

    jobs_ok, messages = smoke.check_recent_jobs("https://example.test", "classics")
    assert jobs_ok is False
    assert any("negative_prompt missing 'airbrushed'" in message for message in messages)
    assert any("prompt does not start with a medium opener" in message for message in messages)


def test_smoke_script_reports_banned_catalog_style_fragments(monkeypatch):
    smoke = _load_smoke_module()

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _fake_get(url, timeout=15):  # type: ignore[no-untyped-def]
        if "/api/prompts" in url:
            return _Response(
                {
                    "prompts": [
                        {
                            "id": "alexandria-wildcard-art-nouveau-poster",
                            "prompt_template": "STYLE: Art Nouveau illustration with gold outlines and decorative elegance.",
                            "negative_prompt": "no vector art, no airbrushed surfaces, no seamless blending, no uniform color fills, no visible circle outline, no wreath, no sunburst",
                        },
                        {"id": "p2"},
                        {"id": "p3"},
                        {"id": "p4"},
                        {"id": "p5"},
                    ]
                }
            )
        return _Response({"jobs": []})

    monkeypatch.setattr(smoke.requests, "get", _fake_get)

    ok, message = smoke.check_prompt_catalog("https://example.test", "classics")
    assert ok is False
    assert "gold outlines" in message
