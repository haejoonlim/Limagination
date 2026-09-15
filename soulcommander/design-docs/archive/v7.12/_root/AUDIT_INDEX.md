# AUDIT_INDEX.md — SOUL COMMANDER Phase 0 종합 감사 인덱스 (Protocol v2.0)

> 작성: 2026-09-07 · 기준 문서: docs/audit/00_protocol.md (§7.3-7.4)
> 감사 문서: 01_baseline · 02_current_architecture · 03_systems · 04_assets_renderer · 05_performance · 06_migration · 07_scenes · ref_ashen_oath (보조)
> 감사 원칙: 실제 실행 결과 > 실제 코드/설정 > 문서(00_protocol.md:16-25) · Unknown ≠ Missing ≠ Broken(00_protocol.md:30-34) · 모든 판정에 Evidence.

---

## 1. Executive Summary

SOUL COMMANDER의 Phase 0 전수 감사 결과, **프로토콜의 "2D→3D 전환" 전제는 이미 수행 완료 상태다** — 전투 런타임은 D-200 Node3D 본전환·D-224 WFC 던전으로 3D 본전환([scenes/Main.tscn]:[26] · [scripts/hero/hero_entity.gd]:[1] · [02_current_architecture.md]:[113-115])이며, 본편 게임플레이 Node2D 잔존 0건([07_scenes.md]:[183]). 코어 루프(ISLAND 준비 → TOWER 전투 → 보상 → 귀환 → 성장)는 코드+실행 양면에서 실제 동작 — headless 표준 스위트 16종 + 보강 7종 = 23종 전부 PASS(exit 0·FAIL 0·SCRIPT ERROR 0, [05_performance.md]:[§3])와 부팅 스모크 전사이클([01_baseline.md]:[73])로 실측됐다.

잔여 갭은 3영역으로 수렴한다: **① 생태계 시뮬레이션 — 런타임 코드 Missing**(74종 카탈로그는 "데이터 정지 상태", [03_systems.md]:[112-122]) **② Git 재현성 — HEAD 체크아웃 Broken**(반쪽커밋 4세트·미병합 브랜치 3건, [03_systems.md]:[30-35,301-304]) **③ 빌드/성능 계측 — Not Found/Unknown**(export_presets.cfg 부재 · FPS baseline 미측정). 아키텍처상 대형 리라이트 대상은 0건이며, 유일한 활성화 과제는 Unwired 스프라이트 라이브러리의 엔티티 연결(옵션 C 확정 시, [04_assets_renderer.md]:[99-101,222])이다.

**이후 절차: Critical Decisions(D2 카드 5건) 사용자 승인 → Phase 1 Architecture Decision 착수.**

---

## 2. Current Baseline (고정값 · 01_baseline.md §1 실측 인용)

| 항목 | 값 | Evidence |
|---|---|---|
| Godot | 4.7.2 stable official · GL Compatibility | [project.godot]:[15,60-61] · [01_baseline.md]:[15-16] |
| 해상도/스트레치 | 1920×1080 · canvas_items/expand | [project.godot]:[29-32] |
| Main Scene | res://scenes/Boot.tscn | [project.godot]:[14] |
| Autoload | 6종 (AssetManager·GSM·SaveManager·AudioManager·AuthService·ApplicationFlow) | [project.godot]:[20-25] |
| 감사 호스트 | macOS · Intel i5-6500 / 8GB / R9 M390 — **프로토콜 Baseline(2015 iMac/8GB)과 동급** | [05_performance.md]:[§1] |
| 테스트 통과율 | headless 23/23 PASS(2026-09-07 실측) | [05_performance.md]:[§3] |
| Export Presets | **Not Found** | [01_baseline.md]:[25] 본 감사 직접 실측 |
| FPS/Frame Time/Memory | **Unknown — Unable to Verify** | [01_baseline.md]:[27] |
| Git | main 브랜치 · Uncommitted 10 modified + 8+ untracked(병행 세션 in-flight) | [01_baseline.md]:[126-129] |

---

## 3. Critical Findings (감사 상위 발견)

| # | Finding | 등급 | 근거 |
|---|---|---|---|
| C-1 | **HEAD 체크아웃 Broken** — 커밋된 loading_screen.gd:55-56이 미커밋 파일을 preload → git clean checkout에서 부팅 파스 에러. 디스크 트리는 실동작 | 긴급 | [03_systems.md]:[30-35] |
| C-2 | **생태 시뮬레이션 Missing** — 프로토콜 §3.14-3.15 대비 런타임 0행. GDD 문서만 존재 | 대형 갭 | [03_systems.md]:[112-122] · [01_baseline.md]:[88] |
| C-3 | **hit_feedback.gd Missing** — STATUS 문서는 "완료" 기록, 파일 부재(데드 참조 audio_manager.gd:270) — Documented ≠ Implemented 실례 | 중 | [03_systems.md]:[175-178] |
| C-4 | **전투 진입 동기 전환** — 유일한 무거운 씬(Main.tscn)이 LoadingScene 우회(dungeon_select.gd:212) | 중 | [02_current_architecture.md]:[182] |
| C-5 | **성능 baseline 전무** — 60FPS 목표에 대한 실측 0. WFC 층당 0.14~0.34s·400 MeshInstance3D만 동급 머신 실측 | 중 | [05_performance.md]:[§4-5] |
| C-6 | **오디오 파일 0개** — 매핑·폴백 코드 선완성, 에셋 Missing(by design) | 중 | [04_assets_renderer.md]:[75-80] |
| C-7 | **깨진 씬 3종**(Probe·Test·AuthFlowTest — 소실 스크립트 참조) + Broken asset_manifest 경로 10건 | 중 | [07_scenes.md]:[153-164] · [04_assets_renderer.md]:[214] |
| C-8 | **Unwired 스프라이트 라이브러리** — 영웅 78조합·몬스터 6템플릿 시스템 완결, 소비자 0건 | 기회 | [04_assets_renderer.md]:[99-101] |
| C-9 | **속성키 비정합 잔존**(air·lightning 2건 · hero_card wind) — 정합 커밋 미병합 | 소 | [03_systems.md]:[114-117,304] |
| C-10 | **Debug overlay·성능 계측 Missing** — DebugLabel은 정적 껍데기([Main.tscn]:[119-124]) | 소 | [05_performance.md]:[§6] |

---

## 4. 감사 항목 인덱스 43 (§7.4 — 각 항목 상태·태그·근거)

상태 어휘: 실제 동작 / 부분 / Missing / Broken / Stub / Unwired / Unknown. 태그: [MIGRATION]·[GREENFIELD]·[HYBRID].

| # | 항목 | 상태 | 태그 | 근거 | 문서 |
|---|---|---|---|---|---|
| 1 | Boot 진입점 | 실제 동작 | [MIGRATION] | [07_scenes.md]:[33-44] | 07 |
| 2 | 인증·세션 (AuthService mock) | 실제 동작 | [HYBRID] | [02_current_architecture.md]:[75] | 02 |
| 3 | 로딩 (스레드 프리로드·폴백 체인) | 실제 동작 | [MIGRATION] | [02_current_architecture.md]:[181] | 02 |
| 4 | MainMenu (체인 고아) | 실구현·미연결 | [HYBRID] | [07_scenes.md]:[129-135] | 07 |
| 5 | HubScene (영지 셸) | 실제 동작 | [HYBRID] | [02_current_architecture.md]:[59-61] | 02 |
| 6 | DungeonSelect (입장·AP 차감) | 실제 동작 | [MIGRATION] | [07_scenes.md]:[99-105] | 07 |
| 7 | Main 전투 씬 (Node3D 본전환) | 실제 동작 | [MIGRATION] | [07_scenes.md]:[107-127] | 07 |
| 8 | 허브 시설 10종 | 실제 동작 | [MIGRATION] | [01_baseline.md]:[109] | 01/03 |
| 9 | 섬 건설·배치 | 실제 동작 | [MIGRATION] | [03_systems.md]:[143] | 03 |
| 10 | 소환 15단계 파이프라인 | 실제 동작 | [MIGRATION] | [01_baseline.md]:[110] | 01 |
| 11 | 편성/파티 5인 | 실제 동작 | [MIGRATION] | [01_baseline.md]:[111] | 01 |
| 12 | 던전 선택·층 입장 | 실제 동작 | [MIGRATION] | [01_baseline.md]:[78] | 01 |
| 13 | AP 경제 (ISS 원장) | 실제 동작 | [MIGRATION] | [02_current_architecture.md]:[87] | 02 |
| 14 | 층 진행 (게이트키퍼 10/15/20) | 부분→실동작 | [MIGRATION] | [01_baseline.md]:[114] | 01 |
| 15 | 자율전투 루프 | 실제 동작 | [MIGRATION] | [03_systems.md]:[160] | 03 |
| 16 | 데미지 파이프라인+지형 보정 | 실제 동작 | [MIGRATION] | [03_systems.md]:[162-164] | 03 |
| 17 | 상태이상/버프/흡혈 | 실제 동작 | [MIGRATION] | [03_systems.md]:[165-166] | 03 |
| 18 | 적 패턴·보스 엔진 | 실제 동작 | [GREENFIELD] | [02_current_architecture.md]:[194] | 02 |
| 19 | 스킬/궁극기 경로 | 실제 동작 | [MIGRATION] | [03_systems.md]:[160] | 03 |
| 20 | hit_feedback (타격감) | Missing (문서상 존재) | [GREENFIELD] | [03_systems.md]:[175-178] | 03 |
| 21 | 월드 UI (HP바·Label3D 빌보드) | 실제 동작 | [MIGRATION] | [03_systems.md]:[232] | 03 |
| 22 | 미니맵 (WFC 20×20) | 실제 동작 | [MIGRATION] | [03_systems.md]:[233] | 03 |
| 23 | WFC 던전 생성기 | 실제 동작 | [MIGRATION] | [02_current_architecture.md]:[193] | 02/05 |
| 24 | 지형 타일 의미·보행 데이터 | 실제 동작 | [MIGRATION] | [03_systems.md]:[250-253] | 03 |
| 25 | 이동/Pathfinding | 미구현 (현설계 불요) | [GREENFIELD] | [03_systems.md]:[254,259-260] | 03 |
| 26 | Physics 충돌 레이어 | 미구현 | [GREENFIELD] | [03_systems.md]:[255-256] | 03 |
| 27 | Camera3D (정적 1대) | 부분 구현 | [MIGRATION] | [03_systems.md]:[268-272] | 03 |
| 28 | Save/Load (단일 덤프+복구) | 실제 동작 | [MIGRATION] | [03_systems.md]:[190-191] | 03 |
| 29 | Schema Versioning | 부분 구현 | [HYBRID] | [03_systems.md]:[198-200] | 03 |
| 30 | World-state 3분리 | 부분 (Persistent 충실) | [HYBRID] | [03_systems.md]:[205-215] | 03 |
| 31 | Scene Transition Transaction | 부분 (동기+저장) | [HYBRID] | [02_current_architecture.md]:[173] | 02 |
| 32 | 생태 시뮬레이션 | Missing (문서만) | [GREENFIELD] | [01_baseline.md]:[88] | 01/03 |
| 33 | 생태 지속성 (offline sim) | 미구현 (선행 미충족) | [GREENFIELD] | [03_systems.md]:[201] | 03 |
| 34 | Renderer (GL Compatibility) | 확정·유지 | [MIGRATION] | [04_assets_renderer.md]:[165-172] | 04 |
| 35 | 영웅 스프라이트 라이브러리 | Unwired (78조합 시스템) | [HYBRID] | [04_assets_renderer.md]:[99-101] | 04 |
| 36 | 몬스터 템플릿·팔레트 | Unwired | [HYBRID] | [04_assets_renderer.md]:[100] | 04 |
| 37 | 배경 4종·폰트 3종·절차 음향 | 실제 동작 | [MIGRATION] | [04_assets_renderer.md]:[35,55-58] | 04 |
| 38 | 오디오 파일·3D 포지셔널 | Missing (by design) | [HYBRID] | [04_assets_renderer.md]:[75-80] · [03_systems.md]:[287] | 04/03 |
| 39 | 3D 모델 파이프라인 | 0개 (전부 절차 생성) | [GREENFIELD] | [04_assets_renderer.md]:[91-95] | 04 |
| 40 | Export/빌드 (Windows/macOS) | 미구성 (Unknown) | [GREENFIELD] | [04_assets_renderer.md]:[179-182] | 04 |
| 41 | 테스트 스위트 27종 | 실제 동작 (headless 23/23 PASS) | [HYBRID] | [05_performance.md]:[§2-3] | 05 |
| 42 | Debug overlay·성능 계측 | Missing | [GREENFIELD] | [05_performance.md]:[§6] | 05 |
| 43 | 구 2D 잔재 5종·깨진 씬 3종·고아 uid | 미사용/깨짐 | [HYBRID] | [02_current_architecture.md]:[132] · [07_scenes.md]:[153-164] | 02/07 |

태그 총계: [MIGRATION] 24 · [GREENFIELD] 12 · [HYBRID] 7 — **전면 재작성(REWRITE) 대상 0건.**

---

## 5. Recommended Next Action

1. **[사용자 승인] Critical Decisions Required — D2 카드 5건** (docs/audit/06_migration.md §4): 비주얼 옵션(D2-1) · 허브 3D 여부(D2-2) · Renderer 유지(D2-3) · Save schema(D2-4) · 잔재 처분(D2-5). 보류 가능: Navigation(D2-6)·생태 범위(D2-7).
2. **[P0] Git 정합**: 반쪽커밋 4세트 완결 커밋 · 미병합 브랜치 3건(terrain 테스트·DeathEpitaph·속성키) 병합 판정 · migration/3d-world 브랜치 체계 채택(00_protocol.md:113-120).
3. **[P1] 옵션 C 확정 시**: AssetManager↔엔티티 빌보드 연결([04_assets_renderer.md]:[222]) — 기존 코드 2계층이 모두 존재하는 유일한 활성화 과제.
4. **[P1] 성능 baseline 1회 실측** + Debug overlay 최소형(FPS·FrameTime 바인딩 — [05_performance.md]:[§8 권고 1-2]).
5. **[P2~] Phase 2 Foundation 착수** — 승인된 ADR 기반 (00_protocol.md:257-259).

---

## 6. 종결

> **AUDIT COMPLETE** — Phase 0 (Protocol v2.0 · READ/INSPECT/ANALYZE/REPORT ONLY 준수 · 기존 파일 무수정)
>
> **Recommended Next Step: Phase 1 — Architecture Decision**
>
> **Critical Decisions Required:** D2-1 비주얼 옵션(A/B/C/D — C 권고) · D2-2 허브 3D 전환 여부 · D2-3 Renderer 유지 · D2-4 Save Schema Versioning · D2-5 구 2D 잔재/깨진 씬/manifest 처분 (+보류 가능: D2-6 Navigation · D2-7 생태 범위)
>
> **Migration Readiness: 조건부 READY** — 코어 루프·Node3D 전환·테스트 안전망은 완성. 선행 조건 2건(Git 정합 P0 · D2 승인) 충족 시 Phase 1 착수 가능. (docs/audit/06_migration.md §6)
>
> **Waiting for approval** — 승인 전 구현·삭제·브랜치 작업 일절 없음 (00_protocol.md §6.3 D2 · PART 8).

---

## 7. Phase 2 부록 (Foundation 산출물 — 연결)

> Phase 2 Foundation(00_protocol.md §6.6)이 기존 Phase 0 감사 인덱스에 추가로 연결하는 산출물.

| # | 문서 | 성격 |
|---|---|---|
| 1 | docs/audit/12_world_units.md | World Units 표준 — 논리 셀=1월드 유닛 고정 · 캐릭터 1.1유닛/반경 0.28 · glTF·MultiMesh 공통 준칙 (ADR-2·ADR-4 연동) |
| 2 | docs/audit/14_character_composer.md | 무한 영웅 3D 부품 조합 인벤토리 — 파츠·아키타입·사상·결정성 계약 (D-243 · GDD §5.2 ⑪ 외형) |
| 3 | docs/audit/15_crowd_instancing.md | MultiMesh 군중 인스턴싱 레이어 — 종별 인스턴싱·주역/군중 전환 계약·10~200 엔티티 측정 (FreeBuff-07 · ADR-4 연동) |
| 4 | docs/audit/19_p1_metrics_zero_win_review.md | P1_METRICS 게이트키퍼 0%-win 벽 리뷰 — 벽 실측 5종·조정안 등가 실측·A+B 채택 적용 + 재실측·회귀 (FB-07 · ★D-269) |
| 5 | docs/audit/20_20f_tmax_recommendation.md | 20층 tmax 660s 연장 재실측 + 권고 — 런타임 무타이머 발견·tmax 520 단축안 기각·tmax 660 채택 권고 (FB-07 후속 · 안건 — 등록 시 D-270 예상) |
| 6 | docs/audit/21_d79_live_comparison_protocol.md | D-79 실전 데이터 ↔ FB-07 벽 대조 선등록 프로토콜 — 데이터·계측기·분석기 3건 미충족 확인 + 판정 기선 고정 (FB-07 후속 · 안건) |
| 7 | docs/audit/18_telegraph_render_correction.md | 진행바 렌더 실측 정정 — D-254 2,384px HP바 오염 판명·기하 타깃팅 교정·10층 보라 1,617/1,512/1,491px 재실측 (FB-03 · ★D-268) |
| 8 | docs/audit/20_landmark_animation.md | 랜드마크 애니 설계·실측 리포트 — 제단 수정 18°/s · 첨탑 오브 야간 펄스(발광 펄스 albedo 바닥 원칙) · FloatRoot 형제 장식 — 슬롯 AABB 계약 보존 · `is_night()` 단일 소스 (FB-05 · D-TBD 결정 대기 · 결정로그 §7 초안 포함) |
| 9 | docs/audit/22_ai_project_brief.md | **AI 작업자용 프로젝트 브리핑** — 저장소 지도·운용 규약·단일 소스 레지스트리(§5) · 전수 감사: 게이트 미등록 하네스 31→25(6종 SUITES 편입)·감사번호 이중 배정 3쌍·D-270 순서 역전·스위트 수 드리프트 원칙 (전체 분석 스윕) |

— END of AUDIT_INDEX.md —
