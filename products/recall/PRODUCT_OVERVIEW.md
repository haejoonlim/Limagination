# Recall — 제품 안내

> 2026-11-26 · LIMAGINATION 공식 프로젝트 · 제품 소속 및 저장소 문서 조사 기준

Recall은 학습 계획, 복습, 집중, 학습 진척을 통합 관리하는 AI 학습 플래너다. 사용자가 지속 가능한 학습 흐름을 유지하도록 돕는다. 상위 브랜드의 헌장과 책임 원칙을 따르되 독립적인 제품 디자인을 유지한다.

## 제품 범위

| 분야 | 저장소에 기록된 기능 |
| --- | --- |
| 학습 계획 | 난이도, 복습 횟수, ease factor, 지연일을 반영한 우선순위와 목표일까지 학습량 배분 |
| 복습 | SM-2 간격 반복 |
| 일정 | 홈, 월간/주간 캘린더, 드래그 일정 조정 |
| 집중과 통계 | 타이머, 학습 진행 통계 |
| AI | Gemini 기반 챗·코칭, 학습 맥락, 적응형 학습 및 동기 부여 기능 후보/기록 |
| 경험 | 테마, 알림, 백업·동기화 설정, 마스코트 및 스와이프 인터랙션 |
| 연동 | ChatGPT MCP를 통한 앱 일정 조회·수정 및 실행 취소 설계 |

## 기술 및 디자인

React 19, TypeScript, Vite, Zustand, Motion, Capacitor 기반. 제품 디자인 시스템은 정보 밀도, 명료한 계층, 접근성 및 정교한 인터랙션을 지향한다. 기존 제품 액센트 #8B5CF6은 상위 브랜드 Muted Amethyst와 별도로 관리한다.

## 근거 및 검증 상태

제품 소스 저장소: [Recall](https://github.com/haejoonlim/recall) (접근 권한 필요).

2026-11-26에 README.md, RECALL_FEATURES_SUMMARY.md, DESIGN_SYSTEM.md, package.json, tools/recall-mcp/README.md 및 src 디렉터리 구조를 확인했다. 위 표는 문서에 기록된 기능이며 이번 조사에서 앱 실행, 각 AI 기능, 동기화, 배포 및 MCP 연결을 재검증하지 않았다. 실제 출시 여부와 버전은 별도 확인한다. 개인 학습 데이터와 연결 자격 증명은 이 브랜드 저장소에 저장하지 않는다.

이전 Recall Infinity 자료는 [기존 제품 가이드](../recall-infinity/PRODUCT_BRAND_GUIDE.md)로 보존한다. 현재 Recall은 공식 프로젝트이며 별도의 두 번째 활성 제품으로 중복 산정하지 않는다.
