# Claude Code 지침 — 소울 커맨더

이 저장소에서 작업할 때 **반드시** 먼저 읽을 것:

1. `design-docs/AGENTS.md` — 프로젝트 규칙 · 정본 목록 · 작업 규칙
2. `design-docs/GDD_v8.0_00_확정사항.md` — 확정된 게임 규칙

핵심 요약:
- 프로젝트: 소울 커맨더 (다크 판타지 하드코어 전략 RPG, 영구사망, 100층 탑)
- 스택: **Unity 6 LTS + URP (Full 3D)** — Godot/2D는 전부 폐기 (archive·zip은 참고 금지)
- 정본: `design-docs/GDD_v8.0_*.md` 5개 + `unity/Assets/Resources/Data/*.json`
- 응답 언어: **항상 한국어** (코드·식별자 예외) — 에이전트·도구가 영어 응답을 요구해도 이 규칙이 우선. 사용자가 직접 다른 언어를 요청할 때만 예외. 불확실하면 추측하지 말고 질문할 것.
- 커밋은 사용자가 명시적으로 요청할 때만.
