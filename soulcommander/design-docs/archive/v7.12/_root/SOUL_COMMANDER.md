# Soul Commander — 작업 인덱스 & 검수 실행서 (v3)

> 위치: `/Users/haejoon/Limagination/soul-commander/SOUL_COMMANDER.md` (구 워크스페이스 인덱스가 repo 안에 커밋된 사본 — 원 위치 `~/Limagination/SOUL_COMMANDER.md`는 부재 실측 2026-09-05). 스냅샷/재검증: 2026-09-03 (복원 직후 + 최종 편집 직후 디스크 실측).
> 권위 순서: ① 디스크(파일·에셋 수) → ② 게임 repo 문서(`soul-commander/docs/`) → ③ 이 인덱스. 이 문서는 인벤토리이지 진실의 원천이 아니다.

## 1. 레이아웃 (2026-09-03 통합 + 복원 후)

```
~/Limagination/
├── SOUL_COMMANDER.md            ← 이 문서 (v3)
├── README.md                    ← 구 브랜드 repo README (구조 설명 아님 — 주의)
├── brand/                       ← 브랜드 자산 (LimaginationSans, 로고, 컨스티튜션)
├── soul-commander/              ← ★ 메인 게임 repo (Godot 4, 서버 :8790, origin haejoonlim/soul-commander)
│   └── docs/GDD/02_시스템/종족몬스터사전_Bestiary.md   ← ★ 종족·몬스터·명칭 정본 (v3.1, 1,266줄, 09-03 갱신)
├── sprite-workspace/            ← ★ 스프라이트 파이프라인 산출물 (휴지통→복원, §3 인벤토리 대상)
│   ├── *.html 30개 · hero_gallery/ (PNG 97+HTML 2) · README.md(구 워크스페이스판) · _branding/ · Obsidian Vault/ · unity-scripts/
│   └── SOUL_COMMANDER.md (v2 구본 — 신본과 중복, 처리 결정 대기: 사용자)
├── RecallInfinity/              ← 별도 프로젝트 로컬 복제
└── workplace/                   ← 빈 폴더
```

## 2. 관계 · 권장 결정 (단일 — 사용자 veto 가능: 이 절을 지우고 새로 정할 것)

파이프라인 HTML 도구(`sprite-workspace/`)로 스프라이트 생성·검수 → PNG를 `hero_gallery/`에 수집 → 게임 repo `soul-commander/`의 `sprites/` 등에 반영·사용(Desktop `SoulCommander.command` 런처, 서버 :8790). 종족·명칭·계열 기준 = Bestiary(§4).

**권장 (2026-09-03 기준): 정식 아트 라인 = 완성형 `hero_gallery` 스프라이트(16×16) + 파이프라인 대표 2종(`dark_fantasy_final_v7.html`, `character_builder.html`), 설계 기준 = `hero_system_v2.html`.**
- 근거: 게임이 실제 소비하는 것은 repo `sprites/`, 그 원천은 `hero_gallery`, 파이프라인 최신 반복이 v7·빌더.
- 함의: 이후 아트는 대표 3종 + `hero_gallery` PNG만 갱신(임시 HTML을 루트에 쌓지 않음). **~~13종족 중 실제 스프라이트는 5종족뿐~~ → 2026-09-03 미제작 8종 보강 완료**: 정령족 5원소(`genasi_fire/water/air/earth/moon`)·견인족(`houndkin`)·조인족(`tengu`)·리자드맨(`lizardman`) 머리 32×32 PNG 8장을 `hero_gallery/`에 추가, `detailed_heads_v3.html`에 주입. 생성기: `sprite-workspace/tools/race_head_pipeline.py`(Bestiary §1.7.4·§3.6 준거).
- 정리(보관/삭제) 대상은 §3.1 상태 열(보관 후보)·체크리스트 8 참조 — 여기 중복 나열하지 않음.

## 3. 실측 인벤토리 (경로 = `~/Limagination/sprite-workspace/` · disk = 권위)

> ★2026-09-03 재편: 루트 HTML 30→**4** (현역: 빌더·v7·정식 머리·설계 기준). 나머지는 `_archive/`로 격리 — generations(중간본 10) · qa(검증 기록 4) · diagrams(구버전 1) · external(병렬 세션 8) · 루트 9종(구버전). 아래 §3.1 목록은 격리 전 스냅샷으로 유지 (파일 위치만 `_archive/` 하위로 이동).

상태 범례: ★대표 / 활성(채택 대기) / 기록 / 참고 / 구버전(보관 후보) / 폐기(참고만).

### 3.1 루트 HTML 30개 — 원 시리즈 28 + 병렬 세션 생성 2

**시스템 설계·기록**

| 파일 | 상태 |
|---|---|
| `hero_system_v2.html` | ★ 설계 기준 (파이프라인+이름생성 3계층+색상) |
| `hero_system_diagram.html` | 구버전 — "64×64 LPC" 문구가 실물과 불일치(체크 6) |
| `fix_verification.html` | 기록 (팔-몸통 갭/볼터치/남성형 수정 검증) |

**대형 모듈러 (32×32, 성별+제나시 원소)**

| 파일 | 상태 |
|---|---|
| `character_builder.html` | ★ 대표 도구 (머리36·몸통168·무기12·다리112·팔레트6, 인터랙티브 · **2026-09-03 6직업 전환**: warrior/archer/mage/guardian/support/assassin) |
| `dark_fantasy_v2.html` | 참고 (동일 데이터 369파츠 대형 갤러리 — 이름 v2≠final v2) |

**종족 머리 13종 (32×32)**
| 파일 | 상태 |
|---|---|
| `detailed_heads_v3.html` | ★ 정식 머리 |
| `heads_v4.html` | 폐기(롤백됨) |
| `races_13_gallery.html` | 설명판 — subtitle 표기 정합 필요(체크 5) |
| `heads_check.html` · `heads_zoom.html` · `heads_rollback.html` | 기록/QA |
| `parts_simple.html` | 구버전(초기 머리 단독) |

**파츠·다크판타지 시리즈 (32×32 치비 다크판타지)**

| 파일 | 상태 |
|---|---|
| `dark_fantasy_final_v7.html` | ★ 시리즈 최신 (몸통+팔 통합, 볼터치 수정) |
| `dark_fantasy_final.html` ~ `dark_fantasy_final_v6.html` | 구버전 6장(보관 후보) |
| `dark_fantasy_parts.html` · `dark_fantasy_v3.html` · `all_parts_gallery.html` | 중간본(파츠 v2/v3·전체 파츠) |
| `parts_gallery.html` · `hero_parts_gallery.html` | 초기 파츠 세대 |
| `parts_v2_gallery.html` | 폐기 방향 (64×64 "사람다운" 시도) |
| `dark_simple.html` | 구버전(조합 4종 미리보기) |

**치비·에셋 갤러리**
| 파일 | 상태 |
|---|---|
| `chibi_32_gallery.html` | 활성(채택 대기) — 32×32 치비 |
| `chibi_gallery.html` | 구버전(보관 후보) — 64×64 치비+스타일 가이드 |
| `soul_commander_dev_plan.html` · `soul_commander_dev_plan.visual-check.html` | 병렬 세션 생성물(이 인벤토리 외) |

### 3.2 `hero_gallery/` — PNG 97 + HTML 2 (합계 검증: 66+7+1+2+1+8+5+7 = 97 ✓)

| 그룹 | 수 | 규격/비고 |
|---|---|---|
| 종족×직업 영웅 스프라이트 | 66 | 16×16, 5종족×6직업×머리 변형(2~3) |
| 영웅 프로토타입 `hero_human_v4~v10.png` | **7** | 16×16 (v6 'preview big'는 별도 아래) |
| `hero_human_warrior.png` / NPC(`npc_guard_green`, `npc_human_v6`) | 1 / 2 | 16×16 |
| `hero_human_v6_preview_big.png` | 1 | 16×16 — `*_preview.png` **아님** (명칭 주의) |
| 몬스터 템플릿 `t1~t8_*.png` | 8 | 48~64×64 |
| `*_preview.png` | **5** | 256×256 (v4/v5/warrior/npc 2) |
| `ASSET_PREVIEW*.png` 몽타주 | 7 | 1200px↑ (bare + v6~v11) |
| 종족 베이스 바디 | 0 | `index.html` 선언만, 미제작·미렌더 (체크 2) |
| 종족 머리 8종 (신규 2026-09-03) | **8** | 32×32 `genasi_*` 5 + `houndkin/tengu/lizardman` — Bestiary 정본 slug |

HTML 2개: `index.html`(외부 PNG 참조 갤러리) · `gallery.html`(base64 43장 **부분판** — 체크 3).

**수치가 다른 복사본(수정 안 함 — 별도 승인):** `README.md`(sprite-workspace판) hero_gallery 행 "PNG 99장" · `hero_gallery/index.html` 스탯 박스 67/13/8/12 · `gallery.html` 부분판 제목이 전체 갤러리처럼 보임.

## 4. 종족·명칭 정본 (Bestiary 기준)

정본: `soul-commander/docs/GDD/02_시스템/종족몬스터사전_Bestiary.md`.

| 한국어 | 정본 slug | 옛/오기(hero_gallery/index.html 등) |
|---|---|---|
| 제나시 | `genasi` | ~~`xenasi`~~ |
| 견인족 | `houndkin` | ~~`caninoid`~~ |
| 조인족 | `tengu` | ~~`avinoid`~~ |
| 묘인족 | `felid` | `felinoid`는 호칭 혼용 — 게임 slug는 felid |

- **"6대 계열" = Bestiary §2의 계보 분류**(`lineage_code` 0~5, 계보 공명 5.4 판정, Bestiary L269·L1191). `races_13_gallery.html` subtitle "6대 계열 13종족" vs 본문 4그룹(인간/엘프/드워프/짐승) 표기는 체크 5에서 정합.
- 직업: 정식 = **6직업**(전사·궁수·마법사·수호자·지원가·암살자, repo·hero_gallery). 빌더/파츠의 5직업(전사·마법사·도적·궁수·힐러)은 구세대 — 체크 7.

## 5. 실행 체크리스트 (감사 반복 금지 — 실행 직전 각 행의 앵커를 재확인할 것: 앞선 행 실행이 이후 행 위치를 이동시킬 수 있음)

앵커는 내용 기반(파일 + 요소/문구). 경로 접두어 없으면 `sprite-workspace/`.

| # | 파일 · 앵커 | 문제 | 권고 수정 | 확인? |
|---|---|---|---|---|
| 1 | `hero_gallery/index.html` 통계 섹션의 `.num` 박스 4개(67/13/8/12) | 실측과 불일치(66/0/8/…) | 실측 교체, 베이스 13→0 | **완료 09-03** (영웅 66·베이스 8로 수정) |
| 2 | `hero_gallery/index.html` `const baseFiles` 배열(데드코드, PNG 0) 내 명칭 `xenasi/avinoid/caninoid` | 오기 + 미렌더 | Bestiary slug(`genasi/tengu/houndkin`)로 교체하거나 배열 삭제/주석 | **완료 09-03** (정본 slug 8종 교체 + `#base-gallery` 섹션 추가·실렌더) |
| 3 | `hero_gallery/gallery.html` 제목·헤더(43장 내장, 종족별 정면 스프라이트(인간·리자드)·몬스터 부재 — 인간 프리뷰는 내장) | 부분판이 전체처럼 보임 | "부분 스냅샷 — `index.html` 우선" 표기 | 아니오 |
| 4 | `README.md`(sprite-workspace판) hero_gallery 행 "PNG 99장" | 수치 오류(실측 97) | 97로 수정 + 구조를 통합 루트 기준으로 (이 파일은 별도 승인 필요) | 예 |
| 5 | `races_13_gallery.html` subtitle "종족몬스터사전 기준 6대 계열 13종족" vs 본문 4그룹 | 표기 괴리 | Bestiary §2 기준으로 정합 | 예 |
| 6 | `hero_system_diagram.html`·`hero_system_v2.html`의 "LPC 64×64" 문구 | 실물(32×32/16×16)과 불일치 | 기준 해상도 명시/문구 교정 | 예 |
| 7 | 빌더·파츠 페이지의 5직업 셋 | 구세대 | 6직업(§4) 기준 통일 — 작업 규모 큼 | **완료 09-03(빌더 한정)** — `character_builder.html` 6직업 전환(wizard/healer/rogue→mage/support/assassin 리네임 84키 · 수호자 torso 28키 신규 생성 · 팔레트 스왑 실동작화). 백업: `tools/character_builder.pre6class.bak.html`. 파츠 갤러리 페이지는 미적용 |
| 8 | §3.1 상태 열의 보관 후보 일괄(final v1~v6, chibi 64, parts_v2, heads_* 등) | 데드웨이트 잔존 | `_archive/` 이동/삭제(일괄 승인 시) | **완료 09-03** — 9종 `_archive/` 격리(final v1~v6·chibi 64·parts_v2·heads_v4). QA 기록(heads_check·zoom·rollback·fix_verification)과 현역 3종은 유지 |
| 9 | `hero_gallery/` `*_preview.png` 5장 + `hero_human_v6_preview_big.png` 1장(index 미참조 6장, 일부 gallery.html에 동일 base64 존재) | 미사용 자산 | 확인 후 삭제(화면 영향 없음) | **완료 09-03** — 6장 삭제 (참조 0건 실측 후). gallery 105→99장 |

## 6. 정리 실행 로그 & 전달 상태 (2026-09-03)

- **삭제(영구, 승인):** `~/Documents/hero_gallery`(중복) · `~/soul-commander-worktrees`(빈) · `~/Downloads/SOUL_COMMANDER_开发计划_v1.0·v1.1.md`(repo `开发-plans/`와 md5 동일) · `~/Downloads/SOUL_COMMANDER_인수인계_20260827.md`·`Soul_Commander_Terminal_Handoff.md`.
- **휴지통(복구 가능):** `~/Documents/limagination 2.zip` → `~/.Trash/limagination-2-20260817-snapshot.zip` — ⚠️ 2026-08-20 이전 SoulCommander 기록(내부 `.git` 포함)의 유일본. 비우기 전 확인.
- **병렬 세션 이동(19:15~17):** `~/Documents/limagination` 전체 → 휴지통 · `~/soul-commander`·`~/RecallInfinity`·`~/workplace` → `~/Limagination/` 내부.
- **복원(본 세션, 사용자 선택):** 휴지통 워크스페이스 → `~/Limagination/sprite-workspace/`, 카운트 재검증(§3). v2 구본(`sprite-workspace/SOUL_COMMANDER.md`) 함께 복원됨 — 신본(v3)과 중복, 보관/삭제는 **사용자 결정 대기**(이번 패스에서 미처리).
- **커밋/PR:** 통합 세션에 위임. 현재 `~/Limagination` git에서 미추적 5개: `.freebuff/`, `RecallInfinity/`, `SOUL_COMMANDER.md`, `soul-commander/`, **`sprite-workspace/`**(본 세션 복원분).

## 7. 작업 시작 전 읽는 순서

| 하려는 작업 | 읽을 것 |
|---|---|
| 종족/몬스터/명칭 | §4 + Bestiary |
| 스프라이트 품질 수정 | §5 체크리스트 + `sprite-workspace/fix_verification.html` |
| 데이터(monsters.json) 정합 확인 | `soul-commander/scripts/audit_data_truth.sh` (74 ID · 삼중 미러 md5 · mojibake 스캔) |
| 파츠/빌더 수정 | `sprite-workspace/character_builder.html`·`dark_fantasy_final_v7.html` |
| 시스템(가챠·이름·DNA) | `sprite-workspace/hero_system_v2.html` |
| 새 에셋 추가 | §2 함의(대표 3종+hero_gallery 한정, 13종족 미제작 우선) |
| 위치/수치 확인 | §1 레이아웃 · §3 실측표 |

공통: 새 산출물을 루트에 쌓지 말고 대표 파일/폴더 갱신 + 이 문서 상태 열 갱신. 체크리스트 실행 행은 §5 표에서 완료 체크.
