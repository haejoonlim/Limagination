# Soul Commander — Unity Rebuild (scaffold)

> 방향 확정: **Full 3D** (D2-1 승인 유지 — 2026-09-14 사용자 확정).
> Godot 실측 자산 재사용: Quaternius/KayKit 3D 모델, composer 파츠 조합 개념,
> MultiMesh 인스턴싱 규약, 119~662 FPS 측정 방법론.

## Setup (Day 0)
1. Unity Hub 설치 → **Unity 6 LTS** + **3D URP Template** 으로 프로젝트 생성
2. 이 폴더 내용을 새 프로젝트 루트에 덮어쓰기 (`Assets/` 구조 + 설정 파일)
3. Personal license (연매출 $200K 미만 무료)
4. `git lfs install` 후 첫 커밋 (PNG/WAV/OGG/TTF 자동 LFS)
5. Godot 백업(`../godot-ver.zip`)에서 가져오기 — **이관 대상만**: 3D 모델 `art/_source/`(Quaternius/KayKit) · `fonts/` → `Assets/Art/Fonts` · `audio/` → `Assets/Art/Audio` · `data/*.json`(구버전 — v8.0은 아래 6번이 정본)
6. **v8.0 데이터 정본은 이미 이 폴더에 있음**: `Assets/Resources/Data/` (monsters 54 · ambient 19 · races 15 · ecology_codex)
   - 설계 기준: `../design-docs/` (v8.0 문서 3개) — `archive/`는 참고 금지
   - ⚠️ 2D 스프라이트(`sprites/`)는 **이관하지 않음** (Full 3D 확정 — `GDD_v8.0_00_확정사항.md` #15)

## 규칙 (Godot에서 배운 것 그대로)
- 세이브 원자성 + 세션 격리 (SaveManager 개념 유지)
- headless 대신 **Unity Test Framework (EditMode)** — 저장 원자성 테스트를 가장 먼저
- Vertical Slice가 끝나기 전에는 풀 커밋 금지 (3주차 고/노-고 게이트)
- 캐릭터: Quaternius/KayKit glTF 임포트 + Humanoid Avatar (composer 개념은 C# CharacterComposer로)
- 한 화면 = 한 설계 (테마는 SoulThemeSO 한 곳에서만)

## Vertical Slice (Weeks 2–3, 고/노-고 게이트)
Boot → Login → Hub → Battle 1회 → defeat → save/reload.
포트 파일: SaveManager, GameState, hero 1종, monster 2종, CHARGE/MOVE/DEFEND 버튼, SoulGauge 1개.
테스트 2~3개 (저장 원자성 우선). 3주차 끝에 계속/축소 결정.

## 폴더 규칙
- `Assets/Scripts/<영역>/` — 영역별 소유권 (Battle/Summon/Estate/UI/Audio/Save/Data/Core)
- `Assets/Tests/` — EditMode 테스트만. PlayMode는 슬라이스 이후
- `Assets/Editor/` — 에디터 도구 (Godot의 art/tools/* 대응)
- `Assets/Resources/Data/` — JSON 런타임 로드 (빠른 길). ScriptableObject bake은 나중에
