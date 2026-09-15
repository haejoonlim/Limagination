# 11_design_decisions.md — Phase 1 Architecture Decision (Protocol v2.0 · §2.3 · §6.3 · §7.5)

> **작성:** 2026-09-07 · Orca 워커 (task_18fee4895037 · dispatch ctx_0df726ed4e62)
> **갱신:** 2026-09-07 · Orca 워커 (task_20c812b8314d) — **D2-2~5 사용자 확정 반영** (§0.1 보드 · §2 카드 · §4 ADR-1/5 승인 · §5 종결)
> **근거 문서:** docs/audit/00_protocol.md (PART 2 · §6.3 Decision Levels · §6.4 [DESIGN DECISION REQUIRED] 포맷 · §7.5 ADR 포맷)
> **선행 산출물:** docs/audit/01_baseline · 02_current_architecture · 03_systems · 04_assets_renderer · 05_performance · 06_migration · 07_scenes · AUDIT_INDEX · ref_ashen_oath
> **문서 성격:** READ/ANALYZE/REPORT + 결정 기록 — 기존 코드·씬·설정·데이터·에셋 무수정(00_protocol.md:39-41). **docs/audit/ 신규 파일(본 문서) 1개만 생성.** Phase 2 구현 0건.
> **Evidence 규칙:** 1차 근거([파일]:[라인])는 본 세션 실측, 2차 인용은 [0X_*.md]:[라인]. 외부 팩 조사는 출처 URL + 실측일(2026-09-07)로 기록.

---

## 0. Executive Summary (한눈 보드)

### 0.1 D2 결정 상태 보드 (사용자 승인 현황)

| 카드 | 주제 | 상태 | 결정/권고 요지 | 본 문서 위치 |
|---|---|---|---|---|
| **D2-1** | 비주얼 아키텍처 (옵션 A/B/C/D) | ★**승인 완료 (Decision = A)** | **A — Full 3D** (3D World+3D Character+3D Monster+3D Environment) | §1 |
| D2-2 | 허브(공중섬) 3D 전환 여부 | ★**확정 (Decision = 권고A2)** | **A2 — 허브 2D 유지(표현 잔류)** · Phase 4(Island Expansion)에서 A1(3D 공중섬) 재판정 | §2.1 |
| D2-3 | Renderer (유지/변경) | ★**확정 (Decision = 유지)** | **gl_compatibility 유지** (desktop·mobile 동일 — ADR-1 승인) | ADR-1 (§4) |
| D2-4 | Save 아키텍처·Schema Versioning | ★**확정 (Decision = S1)** | **S1 — 현 구조 유지 + `save_version` 정수화 분기 훅** (마이그레이션 경로 — ADR-5 승인) | §2.2 |
| D2-5 | 구 2D 잔재·깨진 씬·데이터 정합 처분 | ★**확정 (Decision = R2 변형 · 사용자 결정)** | **R2 폐기 방향** — 2D 스프라이트 에셋 삭제 · 예외: 전투 배경 4종·폰트 3종 **KEEP**(실동작) · **LPC CC-BY-SA 고지 유지** | §2.3 |

보류 확정 대상 (D2-6 Navigation · D2-7 생태 범위) — 옵션 A와 독립적, Phase 5/8 접근 시 별도 결정. 본 문서 범위 밖.

### 0.2 ADR 5건 (§7.5 — Context·Decision·Alternatives·Reason·Trade-offs·Consequences·Evidence)

| ADR | 제목 | Decision (권고/확정) | 승인 상태 | D2 연동 |
|---|---|---|---|---|
| ADR-1 | Renderer | **gl_compatibility 유지** (desktop·mobile 동일) | ★**승인됨 (D2-3 확정)** | D2-3 |
| ADR-2 | World Structure | 단일 전투 월드(Node3D 루트) + WFC 논리 그리드 canonical + **층 조립 비주얼 레이어**(Kit 메시/MultiMesh) | ⬜ 승인 대기 | D2-1 파생 (World Architecture) |
| ADR-3 | Visual Architecture | **옵션 A — Full 3D** (사용자 승인) | ★**승인됨** | D2-1 |
| ADR-4 | Asset Pipeline | 기존 5단계 소싱·라이선스 절차를 **3D 팩으로 확장** + glTF 임포트 + 메시 감사 + MultiMesh 그룹 규약 | ⬜ 승인 대기 (세부 팩 선정은 후속 D2) | D2-5 파생 · ASSET_IMPORT_POLICY §5 |
| ADR-5 | Save | GSM 단일 덤프 유지 + **schema version 분기 훅**(마이그레이션 경로) | ★**승인됨 (D2-4 확정)** | D2-4 |

### 0.3 옵션 A 확정이 전제에 주는 변화 (요약)

1. **Unwired 스프라이트의 역할 전환**: 04_assets_renderer.md의 "옵션 C 확정 시 유일한 연결 과제"(빌보드)는 **해소/폐기 경로로 대체**된다. 캐릭터·몬스터·환경 본체가 3D 메시가 되므로 스프라이트의 런타임 빌보드화는 더 이상 기본 경로가 아니다([04_assets_renderer.md]:[222] 참조의 C 전제 권고).
2. **에셋 제작 부담이 최대로 상승**: 캐릭터/몬스터/환경 전부 신규 3D 에셋 필요 — [04_assets_renderer.md]:[§2.1-2.2]의 "기존 에셋 폐기" 및 "Production Cost 최대" 판정이 그대로 해당한다. 3D 모델 에셋 현 보유 **0개**([04_assets_renderer.md]:[§1.6]).
3. **기존 2D 자산 100% 폐기 금지 원칙 적용(→ D2-5 확정으로 대체)**: 감사 권고는 LPC 영웅 78조합·몬스터 템플릿 6종을 **UI 초상화·도감·로스터 계층으로 재배치 제안**(§3.7)했으나, 사용자 확정(D2-5)은 **R2 폐기 방향** — 2D 스프라이트 에셋 삭제, 단 **전투 배경 4종·폰트 3종은 실동작이라 KEEP**, **LPC CC-BY-SA 고지 유지** (§2.3).
4. **성능 예산·표현 단위 재정의 필요**: 절차 CapsuleMesh/BoxMesh 단순 구조에서 "저폴리 3D 팩 + MultiMesh 인스턴싱" 구조로 전환 예산안(§3.5-3.6). Renderer는 gl_compatibility 유지(D2-3 권고 불변 — §4 ADR-1).
5. **카메라 자유도 제약 제거**: 옵션 C가 전제했던 "빌보드 고정각" 제약이 사라져 카메라 로직(G-4 · §3.7) 확장 여지가 생긴다 — 단 기존 정적 카메라·전투 규칙은 6.2 절(기술/디자인 분리)에 따라 임의 변경 금지.

---

## 1. D2-1 — 비주얼 아키텍처 ★사용자 승인 기록 (Decision = A · Full 3D)

> **[DESIGN DECISION REQUIRED] → 승인 완료** (00_protocol.md §6.3 · 승인자: 사용자 · 2026-09-07)
> 이전 권고(C — 3D World+2D Billboard, [06_migration.md]:[§4 D2-1])를 사용자가 **A로 확정**. 아래 기록은 감사 실측을 유지한 결정 확정 버전이다.

### 1.1 결정 카드

- **Problem:** 유닛 본체가 절차 CapsuleMesh 상태 — 스프라이트 라이브러리(영웅 78조합·몬스터 6템플릿)와 3D 런타임이 미연결(Unwired). 옵션 선택이 기존 에셋 계획을 크게 변경(00_protocol.md:149 조건 해당).
- **Current State:** 3D 루트·절차 지형·빌보드 UI는 실동작 — 그러나 유닛/환경 본체는 절차 프리미티브(옵션 A의 "재료"는 사실상 0). 3D 모델 에셋 0개.
- **Evidence:**
  - 절차 유닛: [scripts/hero/hero_entity.gd]:[1,69-71] `extends Node3D` · `CapsuleMesh(radius 0.28, height 1.1)` / [scripts/hero/enemy_entity.gd]:[73-75] 동일
  - 절차 지형: [scripts/terrain/wfc_dungeon_generator.gd]:[24-25 MAP_W/H=20 · 294-296 TILE_COLORS · 312-344 build_to_world 400개 MeshInstance3D]
  - 3D 모델 에셋 0개: [04_assets_renderer.md]:[§1.6] (`find .glb/.gltf/.obj/.fbx/.blend` = 0)
  - Unwired 실측: [04_assets_renderer.md]:[99-101, §1.7] · 소비자 0건(`grep` 실측)
  - 외부 실증: ref_ashen_oath.md:10-22 (three.js WebGL · InstancedMesh 19종 · SkinnedMesh 7종 · 31 FPS 헤드리스 데모 — 방향성 근거)
- **Options (요약 — 상세는 [06_migration.md]:[§4 D2-1]):**
  - **A Full 3D** — Pros: 표현 일관성 최고 · 카메라 자유 · 향후 표현 확장 용이 / Cons: **기존 스프라이트 본체 사용 불가 · 3D 에셋 전면 신규(GREENFIELD) · Production Cost 최대 · 성능 부담 최고**(2015 iMac R9 M390 / GL Compatibility)
  - B LowPoly+Pixel / C 3D+Billboard / D Hybrid — C는 기존 에셋 직접 재사용·최소 비용이나 빌보드 고정각 전제
- **Decision (= A, 사용자 확정):** 전투 월드·캐릭터·몬스터·환경(지형+소품)을 **전부 3D 에셋 기반으로 전환**. 표현은 "Low Poly + Stylized/Dark Grade"를 기본 방향으로 조사·권고(§3), 아트 스타일 세부는 후속 [DESIGN DECISION REQUIRED]로 분리.
- **근거 (사용자 선택 해석 — 기술 관점 정리):** 캐릭터·몬스터·환경의 시각 일관성과 카메라/표현 자유도를 최우선으로 한다. 표현은 Pixel 제약을 떼고 Low Poly 스타일을 기반으로 한다.
- **Impact:** 전투 비주얼 · 에셋 파이프라인(3D 신설) · AssetManager 소비 경로(스프라이트→UI 초상화 전환) · 성능 예산(MultiMesh/폴리) · Phase 3(3D Vertical Slice) 일정·범위.
- **Risk (등급·완화):**
  - **높음 — 아트/에셋 생산 부담**: 무료 CC0 팩만으로 "13종족×6직업 · 74몬스터" 전수 대응은 불가능 → **모듈러 파츠 + 팔레트 + 스케일 변종**(기존 ASSET_PLAN v1.0 8템플릿 개념을 3D로 승계, §3.4) 및 **대표 모델 우선 + 변종 파생** 전략 권고.
  - **중간 — 시각 톤 전환(픽셀 다크판타지 → 저폴리 3D)**: 기존 픽셀 UI(폰트·팔레트·bg 4종)와의 조화 리스크 → UI 초상화 유지·Dark Grade 라이팅/머티리얼로 완화 (§3.7 · §3.8 리스크표).
  - **중간 — 60FPS**: 프로파일 baseline 미확보(G-12) → §3.5-3.6 예산안을 **Candidate**로 두고 Phase 2/10 계측 전 검증 (프로파일링 없는 성능 주장 금지, 00_protocol.md PART 8).
- **Reversibility:** 중간. 표현 계층 교체이나 에셋·파이프라인 투입이 진행되면 회귀 비용 발생. 되돌림(→C) 시 스프라이트 연결 과제만 복귀.
- **Affected Systems:** hero_entity/enemy_entity(비주얼 슬롯) · WFC 지형 비주얼 레이어 · AssetManager(소비 전환) · 신규 3D 에셋 파이프라인 · 카메라(선택) · UI 초상화 소스.

### 1.2 결정 확정 후속 액션 (권고 — 구현 아님)

1. 옵션 A 구현은 **Phase 3(3D Vertical Slice)부터** 착수 — 그 전 Phase 2 Foundation에서 World Units·데이터·State·Save·씬 생명주기를 먼저 정착(00_protocol.md §6.6-6.7).
2. ADR-2(World Structure) 승인 → WFC 논리 그리드는 그대로 두고 **비주얼 치환 레이어**만 신설 (§4 ADR-2).
3. ADR-4(Asset Pipeline) 승인 + §3 에셋 조사에 기반한 **시드 팩 1종 선정 스파이크**(프로토타입 무게)를 Phase 3 진입 전 1회 수행 — 결정은 사용자.
4. ~~D2-5 재승인 시 LPC 스프라이트를 UI 초상화로 연결하는 소비자 신설(후속 Phase)~~ → **D2-5 확정(2026-09-07)이 R2 변형(폐기 방향)** — 2D 스프라이트 에셋 삭제 · 전투 배경 4종·폰트 3종 KEEP · LPC CC-BY-SA 고지 유지(§2.3).

---

## 2. [DESIGN DECISION REQUIRED] 재작성 — D2-2 · D2-4 · D2-5 (옵션 A 전제 · ★사용자 확정 완료 2026-09-07)

> 아래 3개 카드는 [06_migration.md]:[§4]의 원본 카드를 **"옵션 A(Full 3D) 확정" 전제에서 재평가**한 버전이다. 옵션·근거·권고가 A 전제에서 달라진 항목만 명시하고, 불변 항목은 생략/요약한다. **모두 사용자 확정 완료 (2026-09-07)** — 확정 결과는 §0.1 보드와 각 카드 헤더에 기록(승인 후 구현·삭제·이동은 해당 Phase에서 개별 승인).

### 2.1 D2-2 — 허브(공중섬) 3D 전환 여부 ★확정 (Decision = 권고A2 — 허브 2D 유지 · Phase 4 재판정)

> ★**확정 (2026-09-07)** — 권고 **A2 채택**: 허브(공중섬)는 **지금 2D 유지(표현 잔류)**, Phase 4(Island Expansion)에서 A1(3D 공중섬) 재판정. hub_scene 기능 완결(1100행급) 회귀 방지가 우선.

- **Problem:** 옵션 A 확정으로 **본편(TOWER)이 Full 3D**가 되면, 허브(FLOATING ISLAND)만 2D 픽셀(Node2D)로 남는 **표현 불일치**가 게임 루프(ISLAND↔TOWER 왕복, PART 0 §0.2) 전체에서 노출된다.
- **Current State:** 허브는 Control+Node2D 섬 실동작 — 기능 완결(hub_scene 1,100행급 · 시설 10종)이며 [MIGRATION] 실동작([02_current_architecture.md]:[59-61] · [03_systems.md]:[135-144]). `estate_island.gd:1 extends Node2D` — 배치/그리드 로직이 2D 좌표에 결합([06_migration.md]:[§4 D2-2 Reversibility:중]).
- **Evidence:** [scripts/hub/estate_island.gd]:[1] · [07_scenes.md]:[97] · 04_assets_renderer.md §1.1 (bg_hub 실사용).
- **Options (A 전제 재작성):**
  - **A1 — 3D 공중섬 전환 (권고 방향):** 허브도 3D 월드(Node3D)로 전환, 기존 시설 기능/UI는 유지(표현 계층 교체 + 기능 배선 유지). Pros: 루프 전역 시각 일관성 · 프로토콜 §0.2 구조 정합 · 에셋(저폴리 건물/섬) CC0 소싱 가능. Cons: **대형 GREENFIELD** — estate_island 그리드/배치 로직의 3D 재배선, hub 기능 회귀 리스크. Phase 4(Island Expansion) 전용으로 배정 권고.
  - **A2 — 2D 유지(표현 잔류):** 기능 완결 상태를 우선 보존, Phase 4에서 재평가. Pros: 회귀 0 · Phase 3(Vertical Slice)에 집중. Cons: 옵션 A 취지(전역 Full 3D)와 부분 불일치.
  - **A3 — 하이브리드(3D 배경 + 2D 기능 레이어):** 2D Control UI 위에 3D 공중섬 배경/카메라. Pros: UI 배선 유지가 쉬움. Cons: Control↔3D 혼합 좌표계 복잡도 · 옵션 A 전면 정합 미달.
- **Recommendation (A 전제):** **A2 우선 + Phase 4에서 A1 확정 판정.** 근거: ① Phase 3(3D Vertical Slice) 검증이 먼저(00_protocol.md §6.7) — 허브 전환은 그 뒤가 자연스러운 의존 순서. ② hub_scene 기능 완결(1100행급)을 지금 건드리면 회귀 위험이 Phase 3 증명과 충돌. ③ 단, **"표현은 3D로 간다"는 방향은 A 전제에서 명시**해 Phase 4 설계 시 재작업을 막는다.
- **Impact:** 허브 전면 · Phase 4 · 에셋 소싱(섬/건물 팩 §3).
- **Risk:** A1 즉시 전환 시 hub 기능 회귀(estate_island 배선) · 허브가 먼저 완성될 경우 Phase 4 요구와 충돌.
- **Reversibility:** 중 (표현 계층 교체지만 기능 배선 2D 결합).
- **Affected Systems:** HubScene · estate_island · 시설 UI 10종 · 3D 공중섬 신규.

### 2.2 D2-4 — Save 아키텍처·Schema Versioning ★확정 (Decision = S1 — save_version 분기 훅)

> ★**확정 (2026-09-07)** — 권고 **S1 채택**: GSM 단일 덤프 유지 + `save_version` 정수화 분기 훅(마이그레이션 경로) — 비주얼과 직교, 기존 세이브 v1 호환(ADR-5 승인).

- **Problem:** 옵션 A 도입이 **저장 데이터(게임 상태)에는 직접 변화를 주지 않는다** — 세이브는 논리 상태(로스터·시설·타워 진행·장비)를 저장하며 비주얼 표현과 직교(00_protocol.md §3.12-3.13). 다만 **3D 전환 과정에서 씬 구조·에셋 id·시설 좌표**가 바뀌는 Phase 4/7/8 구간에 스키마 drift 가능성이 커진다 → 마이그레이션 훅의 필요성만 상승.
- **Current State:** 실동작+손상 복구 계약(.corrupt.bak) · 단일 JSON 덤프(`"version": "1.0"`) · 기본값 병합만으로 호환 유지.
- **Evidence:** [scripts/game_scene_manager.gd]:[512 save_path · 514-526 save_game/JSON 직렬화 · 516 "version":"1.0" · 531-544 load/손상 백업] · [03_systems.md]:[198-201 Schema Versioning 부분].
- **Options (A 전제 재작성 — 내용 변경 없음, 비주얼과 직교 재확인):**
  - **S1 (권고) — 현 구조 유지 + 버전 분기 훅 최소 추가:** `save_version` 정수화 + `v1→v2` 마이그레이션 함수 슬롯. 3D 전환의 씬·좌표·에셋 id 변화는 **저장 값 변환이 아니라 로드 타임 정규화**로 흡수(기존 기본값 병합 확장).
  - S2 — SaveManager 승격(원장 이전): Canonical Owner가 GSM으로 일원화된 현실에서 이득 소([02_current_architecture.md]:[96-98]) → 미권고.
  - S3 — 유지(훅 없음): Phase 4+의 스키마 drift 대응 불가 → 미권고.
- **Recommendation (A 전제):** **S1.** 옵션 A가 세이브 포맷을 강제하지 않음 — 비주얼 치환은 "기존 세이브의 논리 상태"를 그대로 로드하고 표현만 바꾸므로 마이그레이션 폭이 작다. 단, **에셋/데이터 참조 키 정합**(몬스터 id·템플릿 id·장비 id)이 3D 파이프라인 전환에서 깨지지 않도록 D2-5(데이터 정합)와 묶어 검증할 것.
- **Impact:** 세이브 호환성 · Phase 9 · 3D 전환 중 로드 정합.
- **Risk:** 스키마 변경 시 기존 세이브 파괴 — [DESIGN DECISION REQUIRED] 요건 유지(00_protocol.md:189).
- **Reversibility:** 낮음(세이브 데이터).
- **Affected Systems:** GSM · SaveManager · 테스트 하네스(격리 규약 — [05_performance.md]:[§2]).

### 2.3 D2-5 — 구 2D 잔재·깨진 씬·데이터 정합 처분 ★확정 (Decision = R2 변형 · 사용자 결정)

> ★**사용자 변형 결정 (2026-09-07)** — 권고 **R1(스프라이트 UI 초상화 유지)을 대체**:
> **R2 폐기 방향 — 2D 스프라이트 에셋 삭제.** 단 예외: **전투 배경 4종·폰트 3종은 실동작이라 KEEP** · **LPC CC-BY-SA 고지 유지**(스프라이트 삭제 후에도 THIRD_PARTY_NOTICES 정책 존속). 깨진 씬 3종(Probe·Test·AuthFlowTest)·asset_manifest 경로 10건은 기존 R1 판단(참조 0건 재검증 후 개별 판결) 유지.

- **Problem:** 옵션 A(Full 3D) 확정으로 **스프라이트의 런타임 유닛 본체화 경로가 사라졌다** — D2-1이 C였을 때의 "hero_sprite/monster_sprite ADAPT로 전환" 판단은 A에서 성립하지 않는다. 반면 **UI 초상화·도감·로스터·메모리얼 계층의 소스**로는 유지 가치가 있다(표현 계층 전환 후에도 2D UI는 픽셀 팔레트·폰트·포트레이트를 쓴다).
- **Current State:** 참조 0건 스크립트 5종 · 깨진 씬 3종(Probe·Test·AuthFlowTest) · Broken asset_manifest 타일 경로 10건 — 전부 실측 완료([06_migration.md]:[§1.3]).
- **Evidence:** [02_current_architecture.md]:[132] · [07_scenes.md]:[153-164] · [04_assets_renderer.md]:[214] · 스프라이트 조합 시스템 [scripts/asset_manager.gd]:[6-8,62-87,127-160] · [scripts/hero_sprite.gd]:[55] · [scripts/monster_sprite.gd]:[64].
- **Options (A 전제 재작성):**
  - **R1 (권고) — 개별 판결 + LPC 스프라이트는 UI 초상화로 유지:**
    - **AssetManager + sprites/(heroes·monsters) 19 PNG + 조합 코드 → KEEP** — 용도를 **UI 초상화·카드·도감·메모리얼**로 재지정하고 신규 소비자(포트레이트 렌더) 연결. 몬스터 팔레트 변종(get_monster_texture)도 도감/HP바 옆 아이콘용으로 유지.
    - `hero_sprite.gd`·`monster_sprite.gd`(런타임 Node2D 유닛 렌더러) → **런타임 사용 경로 폐기(REMOVE 후보)** — 단 AssetManager 조합 API(텍스처 생성)는 위 소비자로 승계하므로 스크립트 자체 판정은 "소비자 전환 후 REMOVE"로 순차 처리.
    - 깨진 씬 3종(Probe·Test·AuthFlowTest) → REMOVE 후보(테스트 하네스 미참조 재확인 후).
    - Broken asset_manifest 타일 경로 10건 → 경로 정합(REPLACE) 또는 해당 항목 REMOVE — 개별 판결.
    - `estate_island`·`hub_scene` 등 허브 기능은 D2-2 판정에 연동(여기서 처분 안 함).
    - 절차 비주얼 코드(BoxMesh/CapsuleMesh)는 **3D 에셋 착수 전까지 placeholder로 KEEP**(폴백 체인 유지 — §3.6).
  - R2 — 일괄 REMOVE: 스프라이트 폐기 — A 전제에서 "UI 초상화 유지 제안"(아래)과 충돌 → 미권고.
  - R3 — 전량 보존: 미사용 껍데기 누적 — 온보딩 혼란 지속 → 미권고.
- **Recommendation (A 전제):** **R1** — 기존 78 LPC 스프라이트(영웅 13종족×6직업)는 **UI 초상화 용도로 유지**한다. 근거: ① 옵션 A에서 3D 캐릭터가 본체가 되어도 2D UI(로스터·소환·편성·기록관·도감)의 초상화 요구는 남는다(픽셀 다크판타지 UI 톤과 3D 본체의 정면 컷이 어긋나는 것보다 일관됨). ② 폐기 금지 원칙(00_protocol.md:153) — 가동 에셋을 값싸게 재배치. ③ AI 몬스터 스프라이트 55종 시트는 **이미 소멸**(client_godot 배포 이력, [04_assets_renderer.md]:[§1.5])이므로 "유지 대상"은 **영웅 78조합 + 몬스터 템플릿 6종 + bg 4종 + 폰트 3종**으로 한정. 단, LPC가 **CC-BY-SA 3.0 파생 라이선스**임을 유지 조건으로 고지(THIRD_PARTY_NOTICES 갱신 — §3.7).
- **Impact:** 코드베이스 위생 · UI 초상화 경로 신설(후속 Phase) · THIRD_PARTY_NOTICES 갱신 · 3D 파이프라인 전환기 정합.
- **Risk:** REMOVE 시 오탈 — 참조 0건 재검증 후 수행. 스프라이트 유지 시 라이선스 고지(SA) 누락 방지.
- **Reversibility:** 높음(git 이력 보존).
- **Affected Systems:** scripts/ 루트(2D 유닛 렌더러) · tests/ 씬 3종 · data/asset_manifest.json · sprites/ · THIRD_PARTY_NOTICES.md · 신규 UI 포트레이트 소비자.

### 2.4 D2-3 — Renderer ★확정 (Decision = gl_compatibility 유지)

> 옵션 A(Full 3D)는 GPU 부하를 올리지만 **렌더러 선택의 결론을 바꾸지 않는다** — 개발 Baseline(2015 iMac R9 M390 · GL 3.3 계열)과 모바일(renderer.mobile=gl_compatibility)을 동시에 만족하는 유일한 계열이므로. **→ 사용자 확정 (2026-09-07): gl_compatibility 유지 (ADR-1 승인).** 감사 권고 "유지"는 [project.godot]:[60-61] 실측과 [04_assets_renderer.md]:[165-173]에 그대로 근거한다.

---

## 3. 옵션 A 에셋 계획 — 무료 CC0 3D 팩 인벤토리 조사 + 라이선스 + 예산안

> **성격:** 조사·권고만 (확정·다운로드·구현 금지 — 00_protocol.md PART 8). 외부 실측일: **2026-09-07**. 팩 라이선스는 **공식 배포 페이지(itch.io/공식 사이트/GitHub 미러) 원문 기준** — 저장소 정책(ASSET_IMPORT_POLICY §2 "원문 대조 후 채택")대로 **도입 전 원문 재대조 의무**가 남는다.

### 3.1 ★명칭 정정 — "KenKit" → "Kenney"

- 조사 결과 **"KenKit"이라는 독립 CC0 3D 팩 패밀리는 존재하지 않는다** (2026-09-07 웹 전수 확인). 요청 문구의 세 소스 "Quaternius·KayKit·KenKit"는 CC0 3D 에셋 생태계의 유명 3총사인 **Quaternius · KayKit(Kay Lousberg) · Kenney(kenney.nl)** 로 해석했다.
- 참고: 저장소는 이미 **Kenney "Roguelike pack"(CC0)** 을 타일·환경·가구로 채택 사용 중([ASSET_IMPORT_POLICY.md]:[41,61-62] D-115/116/118) — 동일 저자의 3D 라인이 이번 조사 대상.
- ⚠️ 만약 "KenKit"이 특정 상용/기타 팩을 지칭했다면 그 존재를 확인하지 못했다 — 지시자에게 확인 필요. 본 문서 §3.3 표의 세 번째 열은 Kenney 기준으로 작성했다.

### 3.2 팩 인벤토리 — 요구 대비 커버리지 (3총사)

게임 요구(옵션 A): ① 영웅 캐릭터(인간형/리깅/애니메이션) ② 클래스 장비·무기 ③ 몬스터(인간형·야수·언데드·원소·마수) ④ 던전/탑 층 환경(모듈러) ⑤ 공중섬·시설(허브, D2-2 연동) ⑥ 소품·데코 ⑦ 애니메이션 ⑧ 파티클/UI 참고.

| 영역 | **Quaternius** (quaternius.com · CC0) | **KayKit** (Kay Lousberg · itch CC0) | **Kenney** (kenney.nl · CC0/Public Domain) |
|---|---|---|---|
| 캐릭터 | Universal Base Characters · Modular Character Outfits-Fantasy(12 아웃핏·62 파츠·색 3변형·Humanoid Rig) | Adventurers(5 리깅+애니 캐릭터 +25 무기/악세서리; Extra +3) | 3D 캐릭터 팩 없음(2D·미니멀 위주) |
| 몬스터 | **Ultimate Monsters(50 애니메이션 몬스터)** · Bestiary-Dungeon Monsters · LowPoly Animated Monsters · LowPoly Animated Animals · Animated Easy Enemies | Skeletons(4 리깅+애니 해골 +10 무기) · Halloween Bits(묘지/언데드 소품) | 없음(캐릭터 계열 부재) |
| 던전/탑 층 | LowPoly Modular Dungeon Pack · Medieval Village MegaKit(300+) · Fantasy Props MegaKit(200+) | **Dungeon Pack(모듈러 던전)** · Medieval Hexagon(200+) · Forest Nature Pack(1588 모델 표기 — 시드 등) · Prototype Bits(64+) | 3D 프로토타입 키트(City/Platformer 등 — 스타일 중립) |
| 허브/시설(D2-2) | Medieval Village MegaKit · Stylized Nature MegaKit(110+, UE/Godot/Unity 프로젝트 동봉) | City Builder Bits · Resource Bits(75+) · Furniture Bits | UI 팩·아이소메트릭 빌딩 계열 |
| 애니메이션 | **Universal Animation Library(120+)** · UAL 2(130+) — Humanoid Rig 리타겟 | KayKit Character Animations(75+) | 스타터 키트(Godot용) |
| 포맷 | FBX · OBJ · glTF · Blend | OBJ · FBX · glTF | OBJ/FBX · PNG · (Godot용 미러) |
| 대표 시트 라이선스 원문 | itch CC0 필드 + quaternius.com "CC0 License" · QAL 페이지 "No attribution required" | itch CC0 필드 + GitHub LICENSE.txt(CC0 1.0) "Free for personal & commercial use" | kenney.nl "License: Creative Commons CC0" · 번들 "Public domain (CC0)" |
| 팩 규모 참고 | 100~300+/팩 다수 | Free 티어 팩당 수십~수백 | 20,000+ 전체(2D+3D 혼합) |

**커버리지 판정 (권고):**
- 몬스터 74종·영웅 다양성 대응은 **단일 팩 불가** → **베이스 리그 4~6종 + 파츠/팔레트/스케일 변종**(기존 8템플릿 모델의 3D화)으로 설계한다. 예: 인간형(Quaternius Universal/Modular 또는 KayKit Adventurers) · 언데드(KayKit Skeletons) · 야수(Quaternius Animated Animals) · 원소/마수(Quaternius Ultimate/Bestiary) · 대형(보스 — 팩+커스텀).
- 던전/탑 층 환경은 **KayKit Dungeon Pack(모듈러)** 을 1순위 후보, 보조로 Quaternius Modular Dungeon/Medieval Village + Fantasy Props.
- **스타일 리스크:** Quaternius/KayKit은 밝은 톤의 스타일라이즈드 로우폴리 — "다크 판타지" 톤과 상충. 완화는 ① 팔레트/머티리얼 리컬러(CC0 허용) ② 조명·포스트 그레이드(gl_compatibility 범위 내) ③ 3D 시각 벤치마크 스파이크에서 검증 — **아트 스타일 통일은 별도 [DESIGN DECISION REQUIRED]로 분리 권고**(기술/디자인 분리 00_protocol.md §6.2).
- Kenney는 본 게임 캐릭터/몬스터 라인으로 **부적합**(스타일·종류 미스매치) — UI·파티클·프로토타입 텍스처·스타터 키트(코드 참고) 용도로만 후보 유지.

### 3.3 라이선스 확인 (CC0 — 공식 페이지 실측 요약 · 2026-09-07)

| 항목 | Quaternius | KayKit (Kay Lousberg) | Kenney |
|---|---|---|---|
| 라이선스 | **CC0 1.0** | **CC0 1.0** (무료 티어) | **CC0 / Public Domain** |
| 상업 사용 | ✅ | ✅ | ✅ |
| 수정/파생 | ✅ (리컬러·파츠 교체 자유) | ✅ | ✅ |
| 재배포 | ✅ (원본 재판매·타인 것 주장 금지 표기 공통) | ✅ (동일 공통 표기) | ✅ |
| 크레딧 | 불필요 (원저자 존중 크레딧은 저장소 정책상 유지) | 불필요 (같음) | 불필요("credit appreciated") |
| 유료 티어 | Source(.blend)·Patreon 얼리 — **무료 티어만 CC0 필수 확인** | Extra/Source는 유료 — **Free 티어만 무료** | 번들(All-in-1)은 유료 — 개별 무료 동일 CC0 |
| 원문 위치 | quaternius.com/license.html · itch 필드 | GitHub KayKit-Game-Assets/LICENSE.txt · itch 필드 | kenney.nl 각 팩 페이지 · 번들 FAQ |
| 저장소 정합 | **CC0만 art/_source 보관** 정책(ASSET_IMPORT_POLICY §5)과 정합 | 동일 정합 | 동일 정합 (기존 Kenney Roguelike 채택 전례) |

**라이선스 조치 (권고):**
1. 채택 시 ASSET_IMPORT_POLICY §2 원문 대조 절차(Original-text verification date 필드)를 **3D 팩에도 동일 적용**, THIRD_PARTY_NOTICES.md 등록.
2. **무료 티어 기준 CC0 재확인** — 유료 티어(Source/Extra) 파일은 저장소에 넣지 않는다.
3. KayKit/Quaternius CC0 페이지의 "원본 무단 재판매·타인 저작물 주장 금지"는 CC0의 윤리적 요청(라이선스상 제약 아님)으로 기록.
4. 3D 에셋 **원본은 art/_source/(gitignored) 보관, 임포트 산출물만 커밋** — 기존 파이프라인 구조(art/out 제외, .gitignore:96,109-131) 승계.

### 3.4 영웅/몬스터 변종 사상 (A 전제 — 기존 78·74 설계의 3D 승계, 권고)

- **영웅 78조합(=13종족×6직업) → "공용 Humanoid 리그 + 종족 시그니처 파츠 + 직업 장비/무기 + 팔레트"** 구조로 사상. 13종족 전부의 **별도 3D 바디 제작은 무료 CC0 팩만으로 불가** — 귀/꼬리/날개/비늘 등 시그니처 파츠(CC0 베이스 + 일부 커스텀)와 피부/헤어 팔레트로 구분. 리그는 Humanoid Rig(Quaternius UAL·KayKit 애니메이션과 리타겟 호환)로 통일.
- **몬스터 74종 → 기존 "템플릿+변종"(ASSET_PLAN_v1.0 §3.2 — 8템플릿)을 3D 베이스 리그 6~8종으로 사상** + 팔레트/스케일/머티리얼 변종. monsters.json(74 id)의 논리 데이터는 무변경 — **비주얼 매핑 레이어만 신설**(Species→3D Mesh/팔레트).
- **데이터/비주얼 분리 준수**: 기존 [scripts/asset_manager.gd]:[62-87,127-160]의 "race×job → 텍스처" 조합 API를 "hero_id/class → 3D 모델 조합"으로 대체하는 것은 **후속 Phase(3+) 구현 과제** — 본 문서는 설계 방향만 기록.

### 3.5 폴리·드로우콜·메모리 예산안 (Candidate — 2015 iMac R9 M390 · 2GB VRAM · 1080p · GL Compatibility · 60FPS)

> ⚠️ **프로파일 baseline 미확보(G-12, [05_performance.md]:[§5.6])** — 아래 수치는 "Budget Candidate → Profile → Actual → Adjust"(00_protocol.md §5.5)의 **후보**다. Phase 2 Debug overlay(+FPS) 또는 Phase 10 계측으로 검증 전 성능 보증·최적화 주장 금지(00_protocol.md PART 8).

**화면 구성 실측 전제**: 직교 카메라 size 6.2([scenes/Main.tscn]:[38-42] projection=1, size=6.2) → 화면 세로 ≈ 12.4m, 1080p ≈ **87px/m**. 캐릭터 1.1m([hero_entity.gd]:[71]) → 화면상 ≈ 96px. 동시 유닛 상한 ≈ 파티5+적 2~8([party_spawner.gd WAVES_1F 웨이브당 2 · 게이트키퍼 부하 ≤4, [05_performance.md]:[§5.2]]).

| 오브젝트 클래스 | 렌더 방식 | 유닛당 폴리 후보 | 인스턴스/DC 후보 | 비고 |
|---|---|---|---|---|
| 지형(층 20×20=400셀) | **MultiMesh** (타일 메시 6종 이하 → 6개 MM) 또는 통합 스태틱 메시 | 셀당 2~24 tris | 400 인스턴스 → **DC 6** | 현행 400개 MeshInstance3D(=400 DC, [05_performance.md]:[§5.1]) 대비 압축. 논리 그리드는 WFC 유지 |
| 층 소품(기둥·횃불·바위·초목) | **MultiMesh** (메시 종류별 1 MM) | 50~400 tris | 층당 100~300 인스턴스 → **DC 5~10** | 총 인스턴스 ≤ 1,500/층 후보 |
| 영웅 (파티 5) | SkinnedMesh(리깅) — 5개 | **≤ 2,000 tris**(액세서리·무기 포함 3,000 상한) | 5 DC | 96px 캐릭터에 2k tris면 충분한 품질 — 스크린 스페이스 근거 |
| 몬스터 (동시 2~8) | SkinnedMesh — ≤8 | 1,500~4,000 (보스 ≤ 8,000) | ≤ 8 DC | 보스는 단독 등장 |
| VFX·월드 UI (HP바·데미지 Label3D) | Sprite3D/Label3D 빌보드 | 소수 사각형 | 기존 유지(풀링 없음 — 확장 시 재평가, [05_performance.md]:[§5.3]) | — |
| **층 합계 후보** | — | **≈ 60k~150k tris/frame** | **DC ≈ 20~35** | 최악(파티5+보스+부하4+소품 풀) 가정 |

- **검증 목표 (Candidate vs 실측 후 조정):** 프레임 예산 16.6ms 중 렌더 슬라이스 목표 < 8ms 여유, **DC < 80**(GL Compatibility·R9 M390 단순 머티리얼 가정), 텍스처 상주 < 256MB(VRAW 2GB 여유 — 8GB RAM baseline과 병행 고려).
- **텍스처 정책 (권고):** 팩 기본 1024² 아틀라스를 층/아크 단위로 분리 로드, 필요 시 512/256 다운샘플(팩 문서상 "128까지 다운샘플 허용" 표기 — KayKit). 프로젝트 전역 `default_texture_filter=0`(Nearest, [project.godot]:[59])는 저폴리 3D 텍스처에서 계단/반짝임 리스크 → 3D 에셋 머티리얼은 Linear+필요 시 mipmap 혼용 검토(아트 벤치마크에서 결정, 임의 변경 금지).
- **MultiMesh 활용 요지(권고):** 정적 반복 메시(지형·소품)는 Godot MultiMesh로 그룹핑 — [ref_ashen_oath.md]:[13,22]의 InstancedMesh 전략과 동일 방향. **스킨드 유닛은 제외**(리깅 애니메이션 개체) — 유닛 수 상한(≤13)이 작아 개별 DC로 충분. 생태계 대량 스폰(Phase 8·74종) 시 **종별 MM(비리깅: 곤충·소형 동물) + 시뮬 LOD**로 확장.

### 3.6 폴백·단계적 전환 (권고 — 구현 아님)

- **Placeholder 유지**: 에셋 도입 전까지 절차 Capsule/BoxMesh 코드는 KEEP — 부팅 스모크·테스트(23종 headless PASS, [05_performance.md]:[§3])가 표현 계층 교체와 무관하게 통과하도록 **비주얼 슬롯 교체형**으로 설계(hero_entity `_build_body`, enemy_entity `_build_body`를 3D 모델 인스턴서로 교체하는 인터페이스만 정의).
- **Phase 3 Vertical Slice**에서 **1종 대표 영웅 + 1종 몬스터 + 던전 타일 1셋**만 3D로 교체해 "3D World 루프"를 증명(00_protocol.md §6.7) → 이후 Phase 4(허브)·5(탑 확장)·6(캐릭터/몬스터)로 확산.
- **기존 2D 계층(UI·폰트·bg·폰트)은 무변경** — 옵션 A는 3D 월드 본체에 한정, Control UI는 지속 사용.

### 3.7 LPC 스프라이트 78조합 — UI 초상화 유지 제안 (D2-5 연동 · 권고)

> ⚠️ **본 제안은 D2-5 사용자 확정(R2 변형 — 2D 스프라이트 에셋 삭제)으로 대체됨 (2026-09-07).** 아래 내용은 감사 권고 기록으로 남기며, 확정 결정은 §2.3·§0.1을 따른다.

- **제안:** 영웅 78조합(13종족×6직업) 합성 시스템([asset_manager.gd]:[62-87])과 19 PNG를 **UI 초상화·로스터·소환·편성·도감·메모리얼용 포트레이트 소스**로 유지한다. 3D 캐릭터가 전투 본체가 되어도 2D UI 계층(픽셀 폰트 Galmuri11·Jacquard24 및 다크판타지 UI 톤)과의 정합성이 초상화에서는 더 높다.
- **런타임 유닛 렌더러(hero_sprite.gd/monster_sprite.gd)는 전환 대상** — 유닛 본체가 3D가 되므로 사용 중단 후 제거/아카이브(소비자 0 실측, [04_assets_renderer.md]:[§1.7]).
- **라이선스 고지 유지:** LPC 파생 스프라이트는 **CC-BY-SA 3.0/GPL 3.0(파츠별)** — UI 초상화로 계속 배포해도 기존 정책(ASSET_IMPORT_POLICY §1 LPC 행 · THIRD_PARTY_NOTICES)이 그대로 적용. 초상화가 UI 내 파생물로 공개 대상임을 THIRD_PARTY_NOTICES 갱신 시 재명시할 것.
- 몬스터 템플릿 6종+팔레트 변종도 동일하게 **도감/전투 시작 정보 UI**용으로 유지 가능(소규모).

### 3.8 위험·오픈 이슈 (에셋 계획)

| # | 리스크 | 등급 | 완화 (권고) |
|---|---|---|---|
| E-1 | 무료 CC0 팩 스타일(밝은 로우폴리) vs 다크판타지 톤 | 중 | 리컬러+그레이드+3D 시각 벤치마크 스파이크 후 아트 방향 [DESIGN DECISION REQUIRED] 분리 |
| E-2 | 13종족 전수 3D 바디 불가 | 높음 | 공용 리그+파츠+팔레트 사상(§3.4) — 게임 디자인 축은 사용자 확인 필요(범위 조정은 6.2 금지 준수) |
| E-3 | 팩 리그·스케일 상이(Retarget 비용) | 중 | Humanoid Rig 통일(Quaternius UAL/KayKit 애니메이션) + 임포트 스케일 규약(1 logical=1m) |
| E-4 | 퍼포먼스 검증 부재 | 중 | §3.5 예산안을 Candidate로, Phase 2 디버그 오버레이로 1차 실측 |
| E-5 | 버전/티어 혼입(유료 티어 파일 커밋) | 소 | 무료 티어만 · ASSET_IMPORT_POLICY §2·§5 자동 감사 연동 |
| E-6 | "KenKit" 명칭 불확정 | 소 | §3.1 정정 — 지시자 확인 필요 |

---

## 4. ADR 5건 (Protocol §7.5 — Context·Decision·Alternatives·Reason·Trade-offs·Consequences·Evidence)

> ADR 상태: **승인됨** = 사용자 승인 완료 / **권고·승인 대기** = Phase 1 카드로 제출, 승인 전 구현 금지(00_protocol.md:253).

### ADR-1 — Renderer (gl_compatibility 유지) [D2-3 연동 · ⬜ 권고·승인 대기]

- **Context:** 60FPS 목표(2015 iMac·R9 M390·2GB)와 향후 iOS/Android 확장. Godot 4.7 GL Compatibility(OpenGL 3.3/ES 3.0 계열)는 구형 GPU·모바일 최광폭 지원. 옵션 A(Full 3D)로 폴리/텍스처 부담은 늘지만 Forward+로의 전환은 Baseline GPU에서 오히려 역효과(Vulkan 요구·모바일 부담).
- **Decision:** **gl_compatibility 유지** — desktop·mobile 동일([project.godot]:[60-61]). 옵션 A에서도 유지. (권고 — D2-3 승인 대기)
- **Alternatives:** Forward+ 전환(고급 라이팅·SDFGI 등) — Baseline·모바일 부적합 · Compatibility 복귀는 저비용 아님.
- **Reason:** [04_assets_renderer.md]:[165-173] 호환 실측 · 모바일 오버라이드 동일 계열 · 커스텀 셰이더 2종 Compatibility 실동작 · 3D 저폴리는 Compatibility에서 충분한 품질.
- **Trade-offs:** 사실 기반 라이팅·고급 후처리 제한 수용 — 현 다크판타지 저폴리 방향과 무충돌(§3).
- **Consequences:** 월드 UI·포스트 그레이드·파티클은 Compatibility 범위 내 구현(라이트 수·섀도 정책은 아트 벤치마크에서 확정). Renderer 변경 시 이 ADR 재개정 필요.
- **Evidence:** [project.godot]:[60-61] · [04_assets_renderer.md]:[165-173] · [05_performance.md]:[§1].

### ADR-2 — World Structure (단일 전투 월드 + WFC 논리 그리드 canonical + 층 조립 비주얼 레이어) [⬜ 권고·승인 대기]

- **Context:** 전투 월드는 Node3D 루트 단일 씬([scenes/Main.tscn]:[26,45]) + WFC 20×20 논리 그리드([wfc_dungeon_generator.gd]:[24-25]) + 스포너 체제([party_spawner.gd])로 실동작. 옵션 A는 "지형 비주얼"을 3D 키트 메시로 교체하되 **게임플레이 로직(걸을 수 있는지·높이·점유)은 논리 그리드**에 남아야 한다(00_protocol.md §2.1 "계산은 3D가 아니라 logical로"). Island↔Tower는 두 씬이 아니라 하나의 루프(World Transition Transaction §3.19).
- **Decision:** **전투/허브 분리 씬 구조는 유지하고, 각 층은 "WFC 논리 그리드 → 층 조립(Node3D 하위 비주얼 컬렉션)"으로 생성**한다. 지형/소품 비주얼은 MultiMesh·모듈러 키트로 조립(§3.5)하고, 논리 그리드(tile_info_at)는 변하지 않는다. 스트리밍/청크 분할은 도입하지 않는다(현 20×20 고정 상수 — [05_performance.md]:[§4]).
- **Alternatives:** (A) Scene 전체 분할(층별 별도 씬 파일) — 세이브/생명주기 복잡 · (B) World Streaming(§3.17 C) — 현 규모 과설계 · (C) 현행 단일 씬+런타임 조립 → **채택(권고)**.
- **Reason:** 실동작 루프(부팅 스모크 전사이클 PASS)를 보존하면서 비주얼만 교체 — 최소 침습. WFC 생성 0.14~0.34s는 층 전환 로딩으로 흡수([05_performance.md]:[§4]).
- **Trade-offs:** 층 크기 확장 시(미래) 조립 구조 재검토 필요 — 20×20 고정이므로 현재 리스크 없음.
- **Consequences:** 신규 비주얼 레이어는 WFC 타일 id → (메시/머티리얼/프로퍼티) 매핑 + 층별 인스턴스 레지스트리. 기존 400 MeshInstance3D 구축은 MultiMesh로 대체(Phase 3+).
- **Evidence:** [Main.tscn]:[26,45-47] · [wfc_dungeon_generator.gd]:[24-25,312-344] · [05_performance.md]:[§4, §5.1].

### ADR-3 — Visual Architecture (옵션 A — Full 3D) [D2-1 연동 · ★승인됨]

- **Context:** D2-1 사용자 승인 완료(2026-09-07). 프로토콜 §2.3 옵션 A: 3D World+3D Character+3D Monster+3D Environment.
- **Decision:** **옵션 A(Full 3D) 채택.** 전투 월드·캐릭터·몬스터·환경을 3D 에셋 기반으로 전환(비주얼 표현). 논리/데이터(종족·몬스터·전투·세이브)는 무변경.
- **Alternatives:** B(LowPoly+Pixel 텍스처 — 스프라이트 부분 재용) · C(3D+Billboard — 감사 원권고) · D(Hybrid) — 사용자 결정으로 A 확정.
- **Reason:** 시각 일관성·카메라 자유 우선(§1.1 근거). 기존 에셋은 UI 초상화로 재배치(D2-5 R1).
- **Trade-offs:** 에셋 생산 부담 최대·성능 부담 최고 → 모듈러/팔레트 변종 + MultiMesh 예산으로 상쇄(§3).
- **Consequences:** Phase 3(3D Vertical Slice)부터 비주얼 치환 · Asset Pipeline ADR-4 필요 · 2D 런타임 유닛 렌더러 퇴역 · UI 초상화 소비자 신설(D2-5 재승인 후).
- **Evidence:** §1.1 Evidence 목록 · [04_assets_renderer.md]:[§2 판정표 A열] · [06_migration.md]:[§4 D2-1].

### ADR-4 — Asset Pipeline (3D CC0 소싱 + glTF 임포트 + 메시 감사 + MultiMesh 그룹 규약) [D2-5·ASSET_IMPORT_POLICY 연동 · ⬜ 권고·승인 대기]

- **Context:** 3D 모델 에셋 0개([04_assets_renderer.md]:[§1.6]) — 옵션 A로 신규 파이프라인 필요. 기존 2D 파이프라인(ASSET_IMPORT_POLICY §1-5 · art/tools 5단계 검토·감사 스크립트 · THIRD_PARTY_NOTICES 표준 필드 · CC0만 _source 보관)을 **확장 재사용**한다. 포맷: 팩 제공 glTF/FBX — Godot 네이티브 glTF를 정식.
- **Decision (권고):** **기존 5단계 소싱 절차를 3D 팩에 동일 적용**하고 다음을 추가한다. ① glTF 임포트 규약(1 logical unit = 1m 스케일 정규화 · 텍스처 아틀라스 분리) ② **메시 감사 스크립트**(임포트 시 tris/bones/머티리얼/텍스처 통계 기록 — §3.5 예산 준수 확인) ③ **MultiMesh 그룹 규약**(정적 반복 메시는 MM으로 — §3.5) ④ 팩별 Humanoid Rig 통일(애니메이션 리타겟 — ADR-2 보조) ⑤ 라이선스: CC0 무료 티어만, THIRD_PARTY_NOTICES 등록(원문 대조일 필드).
- **Alternatives:** FBX 위주 임포트(리깅 보존은 가능하나 glTF 대비 Godot 네이티브 부족) · 2D 파이프라인 그대로(3D 수용 불가) · 신규 툴체인(과설계).
- **Reason:** 기존 절차·감사·라이선스 인프라 재사용(00_protocol.md "재사용 우선") · glTF는 Godot 4.x의 표준 3D 포맷.
- **Trade-offs:** 무료 팩은 스타일/스케일 비정형 → 파이프라인 단계에서 정규화 비용 발생. 팩 확정은 별도 승인(Phase 3 스파이크).
- **Consequences:** 3D 에셋 도입 시점부터 위 규약 적용. art/_source(3D 원본)·imported 산출물 분리. asset_manifest.json에 3D 경로 항목 추가 정합(D2-5).
- **Evidence:** [ASSET_IMPORT_POLICY.md]:[§2-§5] · [04_assets_renderer.md]:[§1.6, §2.1] · §3.2-3.3(본 문서 조사).

### ADR-5 — Save (GSM 단일 덤프 + schema version 분기 훅) [D2-4 연동 · ⬜ 권고·승인 대기]

- **Context:** 단일 JSON 덤프·version "1.0"·손상 백업 실동작([game_scene_manager.gd]:[512-544]) — Canonical Owner는 GSM으로 일원화([02_current_architecture.md]:[96-98]). 옵션 A는 세이브 포맷과 직교(비주얼은 로드된 논리 상태의 표현). 3D 전환 Phase에서 에셋 id·시설 좌표 drift가능성만 상승.
- **Decision (권고):** **GSM 단일 덤프 유지 + 버전 필드를 정수 `save_version`로 승격하고 `v1→v2` 분기/마이그레이션 함수 슬롯 추가**(로드 시 이전 버전을 경유 변환). 비주얼 관련 변화는 저장 값 변환이 아닌 로드 타임 정규화로 흡수.
- **Alternatives:** SaveManager 승격(원장 이전 — 대규모, 이득 소) · 유지(마이그레이션 훅 없음 — Phase 4+ drift 대응 불가).
- **Reason:** 기존 실동작+테스트 격리 하네스(11종 오버라이드·센티널, [05_performance.md]:[§2]) 보존. 최소 침습.
- **Trade-offs:** 세이브 호환 파괴 변경은 향후에도 [DESIGN DECISION REQUIRED](00_protocol.md:189). 훅 추가는 데이터 마이그레이션 코드의 테스트 필요(스키마 회귀).
- **Consequences:** Phase 9(Persistence)·생태 지속성(§3.13·G-1) 진입 시 스키마 확장 지점 제공. 기존 세이브는 v1 경로로 호환.
- **Evidence:** [game_scene_manager.gd]:[512-544] · [03_systems.md]:[198-201] · [05_performance.md]:[§2].

---

## 5. 종결 (Phase 1 출력 요약)

**Phase 1 Architecture Decision — 산출물 (본 문서 1건 · 구현 0건)**

1. **D2-1 = A (Full 3D) — 사용자 승인 확정 기록** (§1).
2. **D2-2·D2-3·D2-4·D2-5 — 사용자 확정 완료 (2026-09-07)**: D2-2=**권고A2**(허브 2D 유지 · Phase 4 재판정) · D2-3=**Renderer 유지**(gl_compatibility — ADR-1 확정) · D2-4=**S1**(save_version 분기 훅 — ADR-5 확정) · D2-5=**R2 변형**(2D 스프라이트 에셋 삭제 · 전투 배경 4종·폰트 3종 KEEP · LPC CC-BY-SA 고지 유지) (§0.1·§2).
3. **ADR 5건 — §7.5 포맷** (§4): **ADR-1 Renderer(승인 — D2-3 확정)** · ADR-2 World Structure(권고) · **ADR-3 Visual Architecture = A(승인)** · ADR-4 Asset Pipeline(권고) · **ADR-5 Save(승인 — D2-4 확정)**.
4. **옵션 A 에셋 계획(조사·권고)** (§3): CC0 3총사(Quaternius·KayKit·Kenney) 인벤토리 · 라이선스 확인 · "KenKit"→Kenney 명칭 정정 · 폴리/MultiMesh/텍스처 예산안(Candidate) · LPC 78조합 UI 초상화 유지 제안.
5. **잔여 승인 대기**: ADR-2(World Structure) · ADR-4(Asset Pipeline — Phase 3 시드 팩 선정) · 보류 D2-6(Navigation)·D2-7(생태 범위). **"KenKit" 명칭 지시 확인**(§3.1) — D2-1~5·ADR-1·ADR-3·ADR-5 확정 완료.

**Recommended Next Step: D2 전수 확정 → Git Checkpoint(G-17) → Phase 2 Foundation** (00_protocol.md §6.5-6.6) — 잔여 승인(ADR-2·ADR-4)은 Phase 2/3 진입 시점에 판정.

**확정 완료 (2026-09-07)** — D2-1~5 전수 사용자 승인. 잔여 보류: D2-6(Navigation)·D2-7(생태 범위) · ADR-2·ADR-4(Phase 2/3 판정). 승인 전 어떤 구현·다운로드·삭제·브랜치 작업도 수행하지 않는다(00_protocol.md:253 · PART 8).

— END of 11_design_decisions.md —
