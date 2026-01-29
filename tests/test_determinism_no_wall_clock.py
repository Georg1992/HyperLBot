#!/usr/bin/env python3
"""Grep-based test: fail if time.time() is used in decision-pipeline modules.

Unified_data timestamp must come from market/candle; no wall-clock in:
- unified_data builder (market_data_service get_unified + orchestration path)
- strategy_manager, prediction_engine, reactive_engine, calibration_hooks
"""

import os


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _grep_time_time(content: str) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(content.splitlines(), 1):
        if "time.time()" not in line:
            continue
        s = line.strip()
        if s.startswith("#"):
            continue
        # Exclude comment-only mention (e.g. "...# ... time.time()") or "instead of time.time()"
        before_comment = line.split("#")[0]
        if "time.time()" not in before_comment:
            continue
        if "instead of time.time()" in line:
            continue
        out.append((i, line.strip()))
    return out


def _extract_method_body(text: str, def_marker: str) -> str:
    start = text.find(def_marker)
    if start < 0:
        return ""
    end = text.find("\n    def ", start + 1)
    if end < 0:
        end = len(text)
    return text[start:end]


def test_no_time_time_in_unified_data_builder():
    """Market data service: get_unified + get_consolidation must not use time.time() for timestamp."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "services", "market_data_service.py")
    text = _read(path)
    for name, marker in [
        ("get_unified_analysis_data", "def get_unified_analysis_data("),
        ("get_consolidation_analysis", "def get_consolidation_analysis("),
    ]:
        body = _extract_method_body(text, marker)
        hits = _grep_time_time(body)
        if hits:
            raise AssertionError(f"market_data_service {name} uses time.time(): {hits}")


def test_no_time_time_in_strategy_manager():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "services", "strategy_manager.py")
    content = _read(path)
    hits = _grep_time_time(content)
    bad = [(n, s) for n, s in hits if not s.strip().startswith("#")]
    if bad:
        raise AssertionError(f"strategy_manager uses time.time() (decision pipeline): {bad}")


def test_no_time_time_in_prediction_engine():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "execution", "prediction_engine.py")
    content = _read(path)
    hits = _grep_time_time(content)
    bad = [(n, s) for n, s in hits if not s.strip().startswith("#")]
    if bad:
        raise AssertionError(f"prediction_engine uses time.time(): {bad}")


def test_no_time_time_in_reactive_engine():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "execution", "reactive_engine.py")
    content = _read(path)
    hits = _grep_time_time(content)
    if hits:
        raise AssertionError(f"reactive_engine uses time.time(): {hits}")


def test_no_time_time_in_calibration_hooks():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "ml", "calibration_hooks.py")
    content = _read(path)
    hits = _grep_time_time(content)
    if hits:
        raise AssertionError(f"calibration_hooks uses time.time(): {hits}")


def test_session_orchestrator_unified_timestamp_from_candle():
    """Orchestrator must use public API for candle timestamp, not time.time() or private attrs."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "services", "session_orchestrator.py")
    content = _read(path)
    if "data_ts = time.time()" in content:
        raise AssertionError("session_orchestrator must not use data_ts = time.time(); use candle timestamp")
    if "get_last_closed_candle_timestamp" not in content or "data_ts" not in content:
        raise AssertionError("session_orchestrator should use get_last_closed_candle_timestamp for data_ts")


def test_orchestrator_no_private_candle_storage():
    """Orchestrator must not reference _candle_storage; use public API only."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "core", "services", "session_orchestrator.py")
    content = _read(path)
    if "._candle_storage" in content:
        raise AssertionError("session_orchestrator must not use _candle_storage; use get_last_closed_candle_timestamp / update_latest_candle")


def test_get_last_closed_candle_timestamp_unsupported_interval_raises():
    """get_last_closed_candle_timestamp(interval != '5m') raises ValueError."""
    import pytest
    from core.services.historical_data_service import HistoricalDataService
    from unittest.mock import MagicMock

    mock_storage = MagicMock()
    mock_storage.get_candle_count.return_value = 1
    mock_storage.get_last_timestamp.return_value = 1000000.0
    mock_storage.backfill_missing_candles = MagicMock()

    svc = HistoricalDataService(cache=MagicMock(), candle_storage=mock_storage)
    assert svc.get_last_closed_candle_timestamp("5m") == 1000000.0
    with pytest.raises(ValueError, match="only supports interval '5m'"):
        svc.get_last_closed_candle_timestamp("1m")
