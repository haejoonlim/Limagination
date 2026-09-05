"""Agent profiles: per-agent model/effort + per-role mapping (no agent calls)."""


def _profiles(monkeypatch, tmp_path, data):
    import json
    from orch import runners
    p = tmp_path / "agents.json"
    if data is not None:
        p.write_text(json.dumps(data) if isinstance(data, dict) else data)
    monkeypatch.setenv("ORCH_AGENTS", str(p))
    return runners


def test_profiles_default_without_file(tmp_path, monkeypatch):
    import os
    from orch import runners
    monkeypatch.setenv("ORCH_AGENTS", str(tmp_path / "missing.json"))
    monkeypatch.delenv("ORCH_CODING_CLI", raising=False)
    prof = runners.load_profiles()
    assert set(prof["agents"]) == {"opencode", "claude", "codex"}
    assert prof["roles"]["analyze"]["agent"] == "opencode"
    assert prof["roles"]["implement"]["agent"] == "opencode"


def test_profiles_file_values_win(tmp_path, monkeypatch):
    runners = _profiles(monkeypatch, tmp_path, {
        "agents": {"opencode": {"enabled": True, "model": "m1", "effort": "high"}},
        "roles": {"analyze": {"agent": "codex", "model": "", "effort": "minimal"}},
    })
    prof = runners.load_profiles()
    assert prof["agents"]["opencode"]["model"] == "m1"
    assert prof["roles"]["analyze"]["agent"] == "codex"
    assert prof["roles"]["implement"]["agent"] == "opencode"  # default kept


def test_profiles_corrupt_file_falls_back(tmp_path, monkeypatch):
    runners = _profiles(monkeypatch, tmp_path, "{not json")
    assert runners.load_profiles()["roles"]["analyze"]["agent"] == "opencode"


def test_model_effort_args_per_runner():
    from orch import runners
    assert runners._model_effort_args("opencode", "m", "high") == ["--model", "m", "--variant", "high"]
    assert runners._model_effort_args("opencode", "", "") == []
    assert runners._model_effort_args("claude", "m", "low") == ["--model", "m", "--effort", "low"]
    assert runners._model_effort_args("codex", "o3", "high") == ["-m", "o3", "-c", 'model_reasoning_effort="high"']
    assert runners._model_effort_args("codex", "", "") == []


def test_run_uses_role_profile(tmp_path, monkeypatch):
    from orch import runners
    _profiles(monkeypatch, tmp_path, {
        "roles": {
            "analyze": {"agent": "opencode", "model": "", "effort": "minimal"},
            "implement": {"agent": "opencode", "model": "m-impl", "effort": "max"},
        },
    })
    monkeypatch.delenv("ORCH_CODING_CLI", raising=False)
    monkeypatch.setattr(runners.shutil, "which", lambda *a: "/bin/x")
    calls = []
    monkeypatch.setattr(runners, "_run",
                        lambda cmd, **kw: (calls.append(cmd) or (0, "ok", None)))
    runners.run_coding_cli("p", forbid_edits=True, cwd=str(tmp_path))
    assert "--variant" in calls[0] and "minimal" in calls[0]
    assert "--model" not in calls[0]
    runners.run_coding_cli("p", forbid_edits=False, cwd=str(tmp_path))
    assert "m-impl" in calls[1] and "max" in calls[1]


def test_fallback_to_installed_enabled(tmp_path, monkeypatch):
    from orch import runners
    _profiles(monkeypatch, tmp_path, {
        "agents": {"opencode": {"enabled": False, "model": "", "effort": ""}},
        "roles": {"implement": {"agent": "opencode", "model": "", "effort": ""}},
    })
    monkeypatch.delenv("ORCH_CODING_CLI", raising=False)
    monkeypatch.setattr(runners.shutil, "which",
                        lambda c: None if c == "opencode" else f"/bin/{c}")
    calls = []
    monkeypatch.setattr(runners, "_run",
                        lambda cmd, **kw: (calls.append(cmd) or (0, "ok", None)))
    runners.run_coding_cli("p", forbid_edits=False, cwd=str(tmp_path))
    assert calls[0][0] == "claude"  # opencode missing+disabled -> next enabled


def test_save_profiles_normalizes(tmp_path, monkeypatch):
    from orch import runners
    monkeypatch.setenv("ORCH_AGENTS", str(tmp_path / "a.json"))
    got = runners.save_profiles({
        "agents": {"opencode": {"enabled": False, "model": "m", "effort": "high", "bogus": 1},
                   "nope": {"enabled": True}},
        "roles": {"analyze": {"agent": "codex", "model": "", "effort": "minimal"},
                  "nope": {}},
    })
    assert got["agents"]["opencode"] == {"enabled": False, "model": "m", "effort": "high"}
    assert "nope" not in got["agents"] and "nope" not in got["roles"]
    assert got["roles"]["analyze"]["agent"] == "codex"
    assert runners.load_profiles() == got  # roundtrip


def test_agents_api_roundtrip(tmp_path, monkeypatch):
    import json
    import socket
    import threading
    from http.server import ThreadingHTTPServer
    from orch import server as s
    monkeypatch.setenv("ORCH_AGENTS", str(tmp_path / "agents.json"))
    state = s.ServerState({})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), s.Handler)
    httpd.state = state
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        port = httpd.server_port

        def call(method, path, body=None):
            sk = socket.create_connection(("127.0.0.1", port), timeout=10)
            raw = json.dumps(body or {}).encode()
            sk.sendall(f"{method} {path} HTTP/1.0\r\nHost: x\r\n"
                       "Content-Type: application/json\r\n"
                       f"Content-Length: {len(raw) if body is not None else 0}\r\n\r\n".encode()
                      + (raw if body is not None else b""))
            sk.settimeout(10)
            blob = b""
            while True:
                chunk = sk.recv(65536)
                if not chunk:
                    break
                blob += chunk
            sk.close()
            return blob.split(b"\r\n\r\n", 1)[1].decode()

        got = json.loads(call("POST", "/api/agents",
                              {"agents": {"opencode": {"enabled": True, "model": "m2", "effort": ""}}}))
        assert got["profiles"]["agents"]["opencode"]["model"] == "m2"
        got = json.loads(call("GET", "/api/agents"))
        assert got["profiles"]["agents"]["opencode"]["model"] == "m2"
        assert "minimal" in got["efforts"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_available_models_opencode_live(monkeypatch):
    from orch import runners
    monkeypatch.setattr(runners, "_run",
                        lambda cmd, **kw: (0, "opencode/m1\nopencode/m2\n", None))
    runners._MODELS_CACHE.update({"ts": 0, "data": {}})
    got = runners.available_models()
    assert got["opencode"] == ["opencode/m1", "opencode/m2"]
    # cached: second call must not re-run
    calls = []
    monkeypatch.setattr(runners, "_run",
                        lambda cmd, **kw: (calls.append(1) or (0, "", None)))
    runners.available_models()
    assert calls == []


def test_available_models_codex_cache(tmp_path, monkeypatch):
    import json
    from orch import runners
    cache = tmp_path / "models_cache.json"
    cache.write_text(json.dumps({"models": [{"slug": "o3"}, {"slug": "gpt-x"}]}))
    monkeypatch.setattr(runners, "_codex_cache_path", lambda: str(cache))
    monkeypatch.setattr(runners, "_run", lambda cmd, **kw: (0, "", None))
    runners._MODELS_CACHE.update({"ts": 0, "data": {}})
    got = runners.available_models()
    assert "o3" in got["codex"]


def test_available_models_claude_curated(monkeypatch):
    from orch import runners
    monkeypatch.setattr(runners, "_run", lambda cmd, **kw: (0, "", None))
    runners._MODELS_CACHE.update({"ts": 0, "data": {}})
    assert runners.available_models()["claude"] == ["sonnet", "opus", "haiku"]


def test_models_api(tmp_path, monkeypatch):
    import json
    import socket
    import threading
    from http.server import ThreadingHTTPServer
    from orch import runners, server as s
    monkeypatch.setattr(runners, "available_models",
                        lambda: {"opencode": ["opencode/m1"], "codex": [], "claude": ["sonnet"]})
    state = s.ServerState({})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), s.Handler)
    httpd.state = state
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        sk = socket.create_connection(("127.0.0.1", httpd.server_port), timeout=10)
        sk.sendall(b"GET /api/models HTTP/1.0\r\nHost: x\r\n\r\n")
        sk.settimeout(10)
        blob = b""
        while True:
            chunk = sk.recv(65536)
            if not chunk:
                break
            blob += chunk
        sk.close()
        body = json.loads(blob.split(b"\r\n\r\n", 1)[1].decode())
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert body == {"opencode": ["opencode/m1"], "codex": [], "claude": ["sonnet"]}


def test_headless_config_denies_dangerous():
    from orch import runners
    perm = runners._HEADLESS_OPENCODE_CONFIG.get("permission", {})
    bash = perm.get("bash", {})
    for denied in ["rm *", "sudo *", "curl *", "wget *",
                   "git push*", "git reset*", "git clean*"]:
        assert bash.get(denied) == "deny", denied
    assert bash.get("*") == "allow"


def test_subagent_passed_to_opencode_only(tmp_path, monkeypatch):
    from orch import runners
    monkeypatch.delenv("ORCH_CODING_CLI", raising=False)
    monkeypatch.setattr(runners.shutil, "which", lambda *a: "/bin/x")
    calls = []
    monkeypatch.setattr(runners, "_run",
                        lambda cmd, **kw: (calls.append(cmd) or (0, "ok", None)))
    prof = runners.default_profiles()
    prof["roles"]["implement"]["subagent"] = "coder"
    monkeypatch.setattr(runners, "load_profiles", lambda: prof)
    runners.run_coding_cli("p", forbid_edits=False, cwd=str(tmp_path))
    assert "--agent" in calls[0] and "coder" in calls[0]
    # analyze keeps its plan agent (subagent field ignored there)
    runners.run_coding_cli("p", forbid_edits=True, cwd=str(tmp_path))
    assert calls[1].count("--agent") == 1 and "plan" in calls[1]


def test_review_role_uses_subagent_or_plan_fallback(tmp_path, monkeypatch):
    from orch import runners
    monkeypatch.delenv("ORCH_CODING_CLI", raising=False)
    monkeypatch.setattr(runners.shutil, "which", lambda *a: "/bin/x")
    calls = []
    monkeypatch.setattr(runners, "_run",
                        lambda cmd, **kw: (calls.append(cmd) or (0, "ok", None)))
    prof = runners.default_profiles()
    prof["roles"]["review"] = {"agent": "opencode", "model": "", "effort": "", "subagent": "reviewer"}
    monkeypatch.setattr(runners, "load_profiles", lambda: prof)
    runners.run_coding_cli("p", forbid_edits=True, cwd=str(tmp_path), role="review")
    assert "--agent" in calls[0] and "reviewer" in calls[0] and "plan" not in calls[0]
    prof["roles"]["review"]["subagent"] = ""
    runners.run_coding_cli("p", forbid_edits=True, cwd=str(tmp_path), role="review")
    assert "plan" in calls[1]
