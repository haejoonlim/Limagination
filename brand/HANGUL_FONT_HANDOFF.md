# Limagination Sans 한글 폰트 — 인계 문서 (HANDOFF)

> 이 문서는 새 작업자(새 채팅의 AI 또는 폰트 디자이너)에게 이 작업을 이어받기 위한
> 인계서다. **이 문서 + 아래 '새 채팅 프롬프트'만 있으면 이전 대화 이력이 필요 없다.**

작성일: 2026-08-06 · 현재 배포 버전: **v13 (Regular) / v12 (Bold)**

---

## 1. 상황 요약

- **제품**: Recall Infinity 앱(React + Vite). 브랜드 폰트 **Limagination Sans**를 사용 중.
- **폰트 구조**: 한글 11,172자는 **자모 합성 엔진**으로 프로그램 생성
  (`build_limagination_full.py`). 라틴·숫자·기호는 image-to-fonts 파이프라인으로
  추출한 글리프를 재사용.
- **핵심 문제**: 사용자가 한글 폰트 품질에 계속 만족하지 못함. 여러 차례 수정을 거쳤지만
  "엉망", "조립식", "이상하다"는 피드백이 반복됨.

---

## 2. 파일 지도 (모든 것이 여기 있음)

| 경로 | 내용 |
|---|---|
| `recall infinity/scripts/recall-font/build_font.py` | 프리미티브(bar_v/bar_h/slanted/ring/vtx/ring_arc + `_capsule`) 정의 |
| `recall infinity/scripts/recall-font/build_limagination_full.py` | **메인 빌더** — 자모 dict + compose() + 기호 재건 + 와인딩 정규화 |
| `recall infinity/scripts/recall-font/build_full_hangul.md` | **수정 이력 문서** (①~⑤-5 전체 — 반드시 읽을 것) |
| `recall infinity/scripts/recall-font/README.md` | 빌드/수정 가이드 |
| `recall infinity/scripts/recall-font/audit-tools/` | **검증 도구 4종 + README** (감각 대신 좌표로 판단) |
| `recall infinity/scripts/recall-font/build/` | 빌드 산출물 (TTF/WOFF2) |
| `recall infinity/public/fonts/` | **앱 배포 위치** (LimaginationSans.woff2 / -Bold.woff2) |
| `recall infinity/src/styles/tokens.css` | @font-face + **캐시버스트 `?v=` 쿼리** (수정 후 반드시 올릴 것) |
| `~/Documents/limagination/fonts/` | **폰트 패키지 배포 위치** (TTF+WOFF2 4종) |
| `~/Documents/limagination/specimen.html` | 견본 페이지 (캐시버스트도 함께 갱신) |
| `~/Documents/limagination/LIMAGINATION_BRAND_CONSTITUTION.txt` | 브랜드 헌장 (폰트 성격 정의) |
| 시스템 참조 폰트 | `/System/Library/Fonts/Supplemental/AppleGothic.ttf`, `/System/Library/Fonts/AppleSDGothicNeo.ttc`, 앱 `public/fonts/PretendardVariable.woff2` |

---

## 3. 이미 고친 것 (다시 고치지 말 것 — 2026-08-06 이력)

1. **와인딩 역전 버그**: 겹치는 획 부위가 nonzero-fill에서 구멍으로 렌더되던 것 → 전
   솔리드 CW·링 홀 CCW 통일 (`_force`).
2. **캡슐 자체교차**: bar 캡이 270° 스윕으로 자체교차 → 획 끝 구멍. `_capsule()`로
   180° 캡 재작성.
3. **no-final 세로모음 기준선**: '가'·'아'가 270유닛 떠 있던 것 → `INITIALS_FULL`/
   `MEDIALS_FULL`(전고 변형)로 기준선 안착.
4. **ㅏ족 갈고리 높이**: 72-83% → 54.5%(받침 없음)/67.5%(받침 있음) — 참조 폰트 정렬.
5. **ㄱ족 세로획**: 중앙 → 좌측(x110, 'ㄴ'과 일관). '⊥' 인상 제거.
6. **기호 전수 재건**: 누락 13 + 잘못매핑 5 + 형상손상 9 + 중복 dedupe + 재중앙화.
7. **라틴 기준선 정규화** (copy_traced) + Bold는 pyclipper 외곽 확장.
8. **● (U+25CF) 추가** (2026-08-06 저녁, v13/v12) — ○와 동일 반지름 디스크.

**현재 감사 결과: 한글 11,172자 cmap 누락 0 · 빈 글리프 0 · x오버플로 0 · 링 홀 14px 개방 ·
기호 누락 0.** (audit-tools/audit_weights.py로 재확인 가능)

---

## 4. 사용자가 아직 보는 문제 (이게 핵심 — 새 작업자가 풀어야 할 것)

사용자의 반복 피드백:
- "한글 폰트가 엉망" — 특히 **limagination/fonts의 TTF를 Font Book/미리보기로 열었을 때**.
- "조립식" — 초성/중성이 각각 그려져 하나의 음절로 안 보인다.
- 특정 글자가 이상하다 (과거 예: 가·든·모의 상단에 떠 있는 요소, 초성과 중성이 분리).

**솔직한 진단 (이 작업의 근본)**: 이 폰트는 막대·원·사선 프리미티브로 자모를 조립해
만든다. 구조는 정확해지지만, **전문 한글 폰트(프리텐다드·애플고딕)처럼 부드럽고
자연스러운 획의 연결·기울기·속도감을 가질 수 없다.** 근본적으로 "그려진 한글"과
"조립된 한글"의 차이다. 각 글자를 개별 수정하면 하나가 좋아지고 다른 하나가 어색해지는
루프가 반복되는 이유이기도 하다.

---

## 5. 현실적인 선택지 (사용자와 상의할 것)

| 선택지 | 장점 | 단점 |
|---|---|---|
| **A. 새 AI 채팅에서 이 문서로 재시도** | 공짜, 이력 문제 해결 | 조립식 한계는 여전 — 스코프를 '구조 정확도'로 제한하면 만족 가능성 있음 |
| **B. 라이선스 OK인 프로 한글 폰트 사용** (Pretendard Rounded, Cafe24 Ssurround 등 — '둥근' 스타일이 리콜과 어울림) | **즉시 완성도**, 리콜 신조에도 부합 | 브랜드 고유 폰트가 아님 (한글만 외부 폰트 + Limagination Sans는 라틴/숫자/로고용) |
| **C. 폰트 디자이너에게 의뢰** (브랜드 폰트의 정공법) | 진짜 브랜드 폰트 | 비용/시간 |
| **D. 지금 폰트를 그대로 쓰고 수정 루프 종료** | 시간 절약 | 사용자가 만족 못 하는 상태 유지 |

**추천**: B가 현실적으로 가장 빠르고 결과물이 좋다. A를 택한다면 아래 프롬프트로 새 채팅을
시작하고, "각 글자를 개별 수정하지 말고, 구조적 결함(빈 글리프·기준선·겹침·홀)만 잡아라"
스코프로 제한하는 것을 권한다.

---

## 6. 재생산/배포 절차 (다음 작업자용)

```bash
# 빌드 (각 4-5분, 반드시 순서대로)
cd 'recall infinity/scripts/recall-font'
python3 build_limagination_full.py            # Regular
python3 build_limagination_full.py --bold     # Bold

# 검증 (좌표로 판단 — 감각 금지)
python3 audit-tools/audit_weights.py
python3 audit-tools/dump_geo.py 가 나 아 한 고 오

# 배포 (MD5 일치 확인)
cp build/LimaginationSans-Full-All.woff2      'public/fonts/LimaginationSans.woff2'
cp build/LimaginationSans-Full-All-Bold.woff2 'public/fonts/LimaginationSans-Bold.woff2'
cp build/*.ttf build/*.woff2                  '~/Documents/limagination/fonts/'

# 캐시버스트 (tokens.css + specimen.html의 ?v= 를 반드시 올릴 것)
# 빌드 검증
cd 'recall infinity' && npx tsc --noEmit && npx vite build
```

---

## 7. 새 채팅에 붙여넣을 프롬프트 (복사용)

```
~/.claude/skills 또는 이 문서 경로를 먼저 읽어주세요:
1) ~/Documents/limagination/HANGUL_FONT_HANDOFF.md (인계서 — 필수)
2) 'recall infinity/scripts/recall-font/build_full_hangul.md' (수정 이력 — 필수)
3) 'recall infinity/scripts/recall-font/audit-tools/README.md' (검증 도구 사용법)

작업:
1. 먼저 limagination/fonts/LimaginationSans-Regular.ttf를 Font Book/미리보기에서
   여는 것처럼 렌더링해서 현재 상태를 눈으로 확인하고,
2. audit-tools/dump_geo.py + render_grid.py로 참조 폰트(Pretendard·AppleGothic)와
   나란히 대조해 문제 음절을 좌표로 확정하고,
3. 근본 원인부터 고치세요. 개별 글자 패치가 아니라 구조적 결함만 다루고,
4. 매 수정 후 audit-tools/audit_weights.py 전수 감사 + 브라우저 검증을 통과해야 합니다.

원칙: 감각으로 판단하지 말고 좌표·렌더로 판단. ㅗ/ㅛ 계열의 기준선은 참조 폰트와
동일한 표준 패턴이므로 '수정'하면 안 됩니다 (인계서 2절 참조).
```

---

## 8. 참고 (디자인 판단 기준)

- 폰트 성격: **호기심(넓은 카운터) · 상상(부드러운 곡선) · 창의(또렷한 획) · 세련(균일) ·
  놀라움(시그니처 디테일)** — 브랜드 헌장 v2.0.
- 자모 dict는 디자인 스템 `S=125` 기준, 웨이트는 `K=STEM/125` 곱 (Regular 110 / Bold 160).
- 셀 존(ZI0/ZV0/ZH0…)은 표준 한글 비례(받침 유무로 상승)를 따름.
- 검증 시 링 홀(ㅇ)·카운터(ㅏ 내부)가 14px에서 막히지 않는지가 소형 가독성의 척도.

**That is the handoff. Good luck. — LIMAGINATION**
