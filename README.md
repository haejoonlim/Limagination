# Limagination

> **We Begin with Imagination.**
> 호기심이 우리의 시작이다. 상상이 우리의 언어다.

LIMAGINATION의 회사 브랜드 자산과 개발 오케스트레이터를 관리하는 저장소입니다. 회사의 철학과 개별 제품의 정체성을 분리해 관리합니다.

## 구조

\`\`\`
├── brand/                         # 회사 고유 자산
│   ├── LIMAGINATION_BRAND_CONSTITUTION.txt
│   ├── LIMAGINATION_BRANDING_REPORT.txt
│   ├── LIMAGINATION_SANS_V2_PROMPT.txt
│   ├── LimaginationSans_사용가이드.txt
│   └── logo / specimen
│
├── products/
│   └── recall-infinity/            # Recall Infinity 앱 전용 문서
│       ├── PRODUCT_BRAND_GUIDE.md
│       └── HANGUL_FONT_HANDOFF.md
│
├── orch/                           # 자율 코딩 오케스트레이터
└── ...
\`\`\`

## 회사 브랜드와 제품의 경계

- **brand/** 는 LIMAGINATION 자체의 미션, 비전, 가치, 행동 원칙과 공통 브랜드 자산만 다룹니다.
- **products/** 는 개별 제품의 사용자, 기능, UI, 말투, 색상, 마스코트, 구현·운영 문서를 다룹니다.
- 제품은 LIMAGINATION의 철학을 바탕으로 만들 수 있지만, 한 제품의 디자인이나 사용 경험을 회사 전체의 신조로 승격하지 않습니다.
- 제품별 기술 문서와 앱 코드는 각 제품 저장소에서 관리합니다.

## 별도 제품 저장소

- **RecallInfinity** — Recall Infinity 앱 본체: https://github.com/haejoonlim/RecallInfinity
- **soul-commander** — 게임 본체: https://github.com/haejoonlim/soul-commander
- **limagination-workspace** — soul-commander 에셋 작업장

