from pocket import probe


def test_api_ok(monkeypatch):
    monkeypatch.setattr(probe, "_http_json", lambda url, timeout=3.0: {"status": "ok", "version": "1.2.3"})
    assert probe.check_api_server().status == "ok"


def test_api_down(monkeypatch):
    monkeypatch.setattr(probe, "_http_json", lambda url, timeout=3.0: None)
    check = probe.check_api_server()
    assert check.status == "fail"
    assert check.fix


def test_dashboard_gate_warn(monkeypatch):
    monkeypatch.setattr(
        probe, "_http_json", lambda url, timeout=3.0: {"auth_required": False, "auth_providers": []}
    )
    assert probe.check_dashboard().status == "warn"


def test_env_check(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / ".env").write_text("API_SERVER_ENABLED=true\n", encoding="utf-8")
    assert probe.check_env().status == "ok"
