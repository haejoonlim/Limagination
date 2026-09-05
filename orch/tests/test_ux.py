"""UX + UI plan tests (no agent calls, no real launches)."""


def test_install_writes_valid_plist(tmp_path, monkeypatch):
    import os
    import plistlib
    from orch import server
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(server, "_launchctl", lambda *a: 0)
    monkeypatch.setattr(server.shutil, "which", lambda *a: ".venv/bin/orch")
    path = server.install_service(8471)
    assert path == str(tmp_path / "Library/LaunchAgents/com.orch.serve.plist")
    data = plistlib.load(open(path, "rb"))
    assert data["Label"] == "com.orch.serve"
    prog = data["ProgramArguments"]
    assert prog[1:] == ["serve", "--port", "8471"]
    assert os.path.isabs(prog[0])  # launchd rejects relative paths
    assert data["RunAtLoad"] is True and data["KeepAlive"] is True


def test_uninstall_removes_plist(tmp_path, monkeypatch):
    from orch import server
    monkeypatch.setenv("HOME", str(tmp_path))
    calls = []
    monkeypatch.setattr(server, "_launchctl", lambda *a: calls.append(a) or 0)
    monkeypatch.setattr(server, "_orch_bin", lambda: "/fake/.venv/bin/orch")
    server.install_service(8471)
    assert server.uninstall_service() is True
    assert not (tmp_path / "Library/LaunchAgents/com.orch.serve.plist").exists()
    assert [c[0] for c in calls] == ["bootstrap", "bootout"]


def test_detect_transitions_only_on_terminal_change():
    from orch import server
    old = {"a": "running", "b": "running", "c": "done"}
    new = {"a": "done", "b": "failed", "c": "done", "d": "done"}
    got = server._detect_transitions(old, new)
    kinds = {(t, s) for t, s, _ in got}
    assert kinds == {("a", "done"), ("b", "failed")}


def test_notify_never_raises(monkeypatch):
    from orch import server
    monkeypatch.setattr(server.sys, "platform", "linux")
    server._notify("t", "m")


def test_phase_of():
    from orch import server as s
    assert s.phase_of({"status": "running", "branch": None}) == "analyzing"
    assert s.phase_of({"status": "running", "branch": "b", "test_result": {}}) == "implementing"
    assert s.phase_of({"status": "running", "branch": "b",
                       "test_result": {"passed": False}, "fix_attempt": 1}) == "fixing"
    assert s.phase_of({"status": "running", "branch": "b",
                       "test_result": {"passed": True}}) == "reviewing"
    assert s.phase_of({"status": "done"}) == "done"
    assert s.phase_of({"status": "failed"}) == "failed"
    assert s.phase_of({"status": "running", "failure_reason": "x"}) == "failed"


def test_help_covers_all_reasons():
    from orch import server as s
    codes = ["implement_crash", "test_failed_exhausted", "timeout", "no_test_command",
             "analyze_error", "lock_unavailable", "secret_detected", "no_changes",
             "dirty_tree", None, "something-new"]
    for c in codes:
        h = s.help_for(c)
        assert set(h) == {"title", "desc", "action"} and all(h.values())


def test_stack_of(tmp_path, monkeypatch):
    from orch import runners, server as s
    py = tmp_path / "py"
    py.mkdir()
    (py / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    assert s.stack_of(str(py)) == "Python/pytest"
    go = tmp_path / "go"
    go.mkdir()
    (go / "project.godot").write_text("[application]\n")
    monkeypatch.setattr(runners, "_godot_binary", lambda: "/fake/godot")
    assert s.stack_of(str(go)) == "Godot"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert s.stack_of(str(empty)) == "테스트 미감지"


def _css():
    import re
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    return src.split("<style>")[1].split("</style>")[0]


def _vars(theme_block):
    import re
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", theme_block))


def _lum(hexcode):
    hexcode = hexcode.strip().lstrip("#")
    r, g, b = (int(hexcode[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a, b):
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_brand_tokens_present():
    css = _css()
    assert "#8B5CF6" in css
    assert "prefers-color-scheme:dark" in css.replace(" ", "")
    assert "--accent-ink" in css


def test_body_contrast_aa_both_themes():
    css = _css()
    light = _vars(css.split(":root")[1].split("}")[0])
    dark_block = css.split("prefers-color-scheme: dark")[1]
    dark = _vars(dark_block.split("{", 1)[1].rsplit("}", 1)[0])
    assert _ratio(light["--text-primary"], light["--bg-canvas"]) >= 4.5
    assert _ratio(dark["--text-primary"], dark["--bg-canvas"]) >= 4.5
    assert _ratio(light["--accent-ink"], light["--bg-canvas"]) >= 4.5

def test_contrast_clone():
    css = _css()
    light = _vars(css.split(":root")[1].split("}")[0])
    assert _ratio(light["--text-primary"], light["--bg-canvas"]) >= 4.5


def test_app_layout_ids():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    for eid in ["app-header", "repo-tabs", "run-panel", "task-table",
                "LIMAGINATION", "Made with LIMAGINATION"]:
        assert eid in src


def test_state_experience_markup():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "phase-steps" in src
    assert "empty-tasks" in src
    assert "grad-brand" in src or "celebrate" in src
    assert "아직 작업이 없어" in src


def test_brand_voice():
    import re
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    for banned in ["처리되었습니다", "왜 안 했", "실패했습니다"]:
        assert banned not in src
    for m in re.finditer(r'[가-힣][^<>]{0,80}', src):
        emojis = len(re.findall(r'[\U0001F300-\U0001FAFF☀-➿⚡🌱🔧✅❌]', m.group(0)))
        assert emojis <= 2, m.group(0)[:40]
    for must in ["잠깐만", "시작할게", "확인해줘"]:
        assert must in src


def test_korean_type_stack():
    import re
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "Pretendard" in src
    assert "@import" not in src and "fonts.googleapis" not in src
    m = re.search(r"font-family:\s*([^;]+);", src)
    assert m and "system-ui" in m.group(1)


def test_dashboard_korean_chrome():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    for must in ["<th>작업</th>", "<th>상태</th>", "STEP_OF", "fixing: 2"]:
        assert must in src
    assert "<th>task</th>" not in src


def test_record_history_emits_on_phase_change_only():
    from orch import server as s
    import threading
    st = s.ServerState({})
    ev1 = s._record_history(st, {"a": ("analyzing", "running")})
    assert [(e["task_id"], e["phase"]) for e in ev1] == [("a", "analyzing")]
    assert s._record_history(st, {"a": ("analyzing", "running")}) == []
    ev2 = s._record_history(st, {"a": ("implementing", "running")})
    assert [(e["task_id"], e["phase"]) for e in ev2] == [("a", "implementing")]


def test_sse_log_replays_history(tmp_path, monkeypatch):
    import socket
    import threading
    from http.server import ThreadingHTTPServer
    from orch import server as s
    monkeypatch.setenv("ORCH_REPOS", str(tmp_path / "repos.json"))
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / ".git").mkdir()
    s.save_registry({"t": str(repo)})
    state = s.ServerState(s.load_registry())
    with state.mu:
        state.history["cli-9"] = [
            {"ts": 1.0, "phase": "analyzing", "status": "running"},
            {"ts": 2.0, "phase": "implementing", "status": "running"},
        ]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), s.Handler)
    httpd.state = state
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    try:
        sk = socket.create_connection(("127.0.0.1", httpd.server_port), timeout=10)
        sk.sendall(b"GET /api/log?task=cli-9 HTTP/1.0\r\nHost: x\r\n\r\n")
        sk.settimeout(10)
        blob = b""
        while blob.count(b"data: ") < 2:
            chunk = sk.recv(4096)
            if not chunk:
                break
            blob += chunk
        text = blob.decode()
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert "text/event-stream" in text
    assert text.count("data: ") >= 2
    assert "implementing" in text


def test_detail_view_markup():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "toggleDetail" in src
    assert "EventSource" in src and "/api/log?task=" in src
    assert "detail-plan" in src and "detail-timeline" in src


def test_theme_toggle_markup():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "data-theme" in src
    assert "orch-theme" in src
    assert "theme-toggle" in src


def test_polish_round1_no_help_without_reason():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "reasonText" in src
    assert "thead th" in src and "white-space: nowrap" in src
    assert "taskid" in src


def test_polish_round2_ellipsis_and_celebrate():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "td.trunc" in src and "text-overflow: ellipsis" in src
    assert "box-shadow: inset 3px 0 0 #8B5CF6" in src
    assert "border-image" not in src


def test_inputs_themed():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "textarea {" in src and "background: var(--bg-canvas)" in src
    assert "input, select" in src


def test_detail_survives_refresh():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "openDetailTask" in src
    assert "renderDetailRow" in src


def test_detail_pre_wraps():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert ".detail-plan pre" in src and "pre-wrap" in src


def test_model_picker_markup():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "modelCell" in src and "data-msel" in src
    assert "/api/models" in src and "__custom__" in src


def test_install_sets_service_path(tmp_path, monkeypatch):
    import plistlib
    from orch import server
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setattr(server, "_launchctl", lambda *a: 0)
    monkeypatch.setattr(server, "_orch_bin", lambda: "/x/orch")
    path = server.install_service(8471)
    data = plistlib.load(open(path, "rb"))
    env_path = data["EnvironmentVariables"]["PATH"]
    assert ".opencode/bin" in env_path and ".local/bin" in env_path
    assert env_path.startswith("/usr/bin:/bin")


def test_simplified_layout():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "<th>브랜치</th>" not in src  # A1: branch lives in detail only
    assert "agentsummary" in src  # A3: mapping summary when panel closed
    assert "detail-branch" in src  # A1: branch shown in detail row


def test_role_subagent_input_present():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert 'data-k="subagent"' in src
    assert "<th>서브에이전트</th>" in src


def test_phase_reviewing():
    from orch import server as s
    assert s.phase_of({"status": "running", "branch": "b",
                       "test_result": {"passed": True}}) == "reviewing"
    assert s.phase_of({"status": "running", "branch": "b", "test_result": {"passed": True},
                       "review_passed": True}) == "pr"


def test_review_role_row_renders():
    src = open("src/orch/dashboard.html", encoding="utf-8").read()
    assert "review" in src and "리뷰" in src
    assert "reviewing" in src and "검토 중" in src
