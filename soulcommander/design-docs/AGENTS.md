# AGENTS.md — 프로젝트 전역 지침 (v8.0)

> 이 파일은 소울 커맨더 작업 시 **반드시 먼저 읽는** 표준입니다.
> 최종갱신: 2026-09-14 · 기준: **GDD v8.0 + Unity 전환**

---

## 1. 프로젝트

- **이름:** 《소울 커맨더 (Soul Commander)》
- **장르:** 다크 판타지 하드코어 전략 RPG — 영구사망 · 100층 탑 · 영지 경영
- **현재 단계:** **v8.0 리부트** — GDD 전면 재작성 + **Unity(Full 3D) 신규 개발**
- **제작 방식:** 인디 (Steam $15~20 일회성 구매, 라이브서비스·과금 없음)

## 2. 정본 (Single Source of Truth)

**아래 5개 문서 + Unity 데이터 JSON만 정본이다. 나머지는 전부 역사자료.**

| 정본 | 내용 |
|---|---|
| `design-docs/GDD_v8.0_00_확정사항.md` | 확정 결정 목록 (여기 없는 건 미정) |
| `design-docs/GDD_v8.0_01_등급_전투력.md` | ★1~★7 등급계수 + 전투력(CP) 공식 |
| `design-docs/GDD_v8.0_02_생태사전.md` | 비전투 생물 19종 + 층별 출현 |
| `design-docs/GDD_v8.0_03_개발플랜.md` | Phase 0~5 개발 진행 기준 |
| `design-docs/GDD_v8.0_04_영지.md` | 영지(시설 12종·인구·채집·농사·식량·민심·칙령) 확정 |
| `design-docs/GDD_v8.0_05_영웅생성.md` | 영웅 생성 13단계 파이프라인 확정 |
| `design-docs/GDD_v8.0_06_바이옴.md` | 바이옴 20종 (10+9+1) · 5층 블록 슬롯 배정 · 난이도 (가안) |
| `unity/Assets/Resources/Data/monsters.json` | 전투 몬스터 **54종** (스키마+스탯+패턴+스폰+생태) |
| `unity/Assets/Resources/Data/ambient.json` | 비전투 19종 원본 데이터 |
| `unity/Assets/Resources/Data/races.json` | 플레이어블 **15종** + 계열6 + 공명 |
| `unity/Assets/Resources/Data/ecology_codex.json` | 생태사전 데이터 |
| `unity/Assets/Resources/Data/biomes.json` | 바이옴 데이터 20종 (가안 — 06 문서) |
| `unity/Assets/Resources/Data/equipment.json` | 장비 최소 세트 9종 (가안 — P3-3) |
| `design-docs/_tools/check_docs.py` | 정합 검증 (JSON·필수문서·구수치·구경로 — exit 0) |
| `unity/THIRD_PARTY_NOTICES.md` | 서드파티 라이선스 고지 |

- **archive/는 읽지 말 것** — Godot v7.12 이전 역사기록. 수정 금지.
- Godot 구현체는 `soulcommander/godot-ver.zip`으로 프리즈 (참조 전용, 부활 금지).

## 3. 읽는 순서 (작업 착수 시)

1. 이 파일 (AGENTS.md)
2. `GDD_v8.0_00_확정사항.md` — 뭐가 확정인지
3. 해당 도메인 문서: 등급/CP면 01, 생태면 02, 몬스터/종족이면 Data JSON
4. 확정사항에 없는 내용은 **추측하지 말고 사용자에게 확인**

## 4. 핵심 게임 규칙 요약 (v8.0 확정)

| 항목 | 값 |
|---|---|
| 파티 | 출격 5인 · 예비 없음 · 사망 시 교체불가 (전력 영구감소) |
| 사망 | 영구사망. 병원은 생존자 요양(Sanity)만 — 부활 금지 |
| 행동력(AP) | MAX 30 · 시간회복 없음 · 적 처치 +1 · 일반층 2 / 게이트키퍼 3 |
| 전투 | 1~3층 완전자동 / 4층+ 전술개입 (전술게이지 최대100·시작50·초당+2·처치+10) |
| 데미지 | 감소율 = DEF/(DEF+200) · 관통 = `(DEF×(1-pen))/(DEF×(1-pen)+200)` |
| 위치보정 | 측면 +10% / 배후 +25% / 고지대 +15% / 커버 ×0.75 |
| 소환 | ★1~★6 뽑기 · **★7은 초월진화 전용** · 천장 미정(공란) |
| 등급계수 | ★1 ×1.00 ~ ★6 ×3.71, ★7 ×4.83 (등급당 ×1.3 복리) |
| 전투력 | `CP = (스탯×등급×레벨 + 장비 + 스킬) × 성격 × 상태 × 공명` (01 문서) |
| 몬스터 | 전투 54종 + 앰비언트 19종 |
| 종족 | 플레이어블 15종 / 6계열 / 아종 34종 |
| 레벨상한 | 전 등급 Lv100 |
| 경제 | 골드100×층 · 영혼석(하) 층×30+게이트잭팟(퇴장지급) · 경험치80×층 · 소환티켓 130석 |

## 5. Unity 개발 규칙

- **엔진:** Unity 6 LTS + URP (3D 템플릿)
- **프로젝트 루트:** `soulcommander/unity/` (Unity Hub에서 이 폴더를 프로젝트로 열거나, 새 프로젝트 생성 후 Assets/ 구조 덮어쓰기 — `unity/README.md` 참조)
- **언어:** C# · 테스트는 Unity Test Framework (EditMode)
- **데이터:** `Assets/Resources/Data/*.json` 런타임 직로드 (ScriptableObject bake은 후속)
- **세이브:** 단일 JSON 덤프 + 원자성(임시파일→교체) + 손상 시 .corrupt.bak · 세션 격리
- **3D 에셋:** Quaternius/KayKit glTF 우선 (godot-ver.zip의 art/_source에 실물 있음)
- **자산 규칙:** 라이선스 확인 → 서드파티 고지 문서(Unity 프로젝트에 THIRD_PARTY_NOTICES.md 신설)에 기록 (CC0 우선)
- 상세: `unity/README.md` · `unity/PORTING_MAP.md`

## 6. 작업 규칙

0. **응답 언어 = 한국어** (코드·식별자 예외)
1. **정본 우선** — §2의 파일이 최신. archive/ 문서를 근거로 인용 금지
2. **한 스텝에 하나만** — 완료 확인 후 다음
3. **불확실하면 질문** — 추측 금지
4. **수치 변경 시** — 관련 정본 문서(00/01/02)와 Data JSON을 같은 작업에서 함께 갱신
5. **문서 신규 작성 시** — `_템플릿/` 사용, 문서 상단에 프론트매터(작성일·기준버전) 기록
6. **커밋은 사용자가 명시적으로 요청할 때만**

---

## 변경 이력

| 날짜 | 변경 |
|---|---|
| 2026-09-14 | v8.0 전면 재작성 — Unity/Full3D 전환, 구 Godot 지침·AUDIT_INDEX·SOUL_COMMANDER·11_design_decisions를 archive/v7.12/_root/로 격리 |
| (이전) | 구 Godot 기준 지침은 `archive/v7.12/_root/AGENTS.md` 참조 |
