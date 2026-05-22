import pytest

from talent_intel_crm import telemetry


def test_measure_emits_success_metric(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(telemetry, "emit_metric", lambda name, **fields: events.append((name, fields)))

    result = telemetry.measure("metric.test", lambda: "ok", tenant_id="tenant-001")

    assert result == "ok"
    assert events[0][0] == "metric.test"
    assert events[0][1]["outcome"] == "success"


def test_measure_emits_failure_metric(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(telemetry, "emit_metric", lambda name, **fields: events.append((name, fields)))

    with pytest.raises(RuntimeError):
        telemetry.measure("metric.test", lambda: (_ for _ in ()).throw(RuntimeError("fail")))

    assert events[0][1]["outcome"] == "failure"
    assert events[0][1]["error_type"] == "RuntimeError"
