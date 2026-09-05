# Limagination

> **We Begin with Imagination.**
> 호기심이 우리의 시작이다. 상상이 우리의 언어다.

Limagination의 **브랜드 자산 + orch 오케스트레이터** 공식 저장소입니다.

## 구조

이 저장소는 두 프로젝트의 코드를 포함하지 않습니다. 아래 디렉터리는 **각자의 원격을 가진 별도 저장소**가 작업 공간에 함께 체크아웃된 것입니다.

```
├── brand/           # 브랜드 자산 (헌장·리포트·폰트·로고) — 이 저장소 소유
├── orch/            # langgraph 자율 코딩 오케스트레이터 — 이 저장소 소유
└── (작업 공간에 함께 체크아웃된 별도 저장소)
    ├── soul-commander/   → https://github.com/haejoonlim/soul-commander
    │                        ★ 게임 본체 (Godot 4.7.2 · GDD v7.12)
    │                        진입점: soul-commander/docs/STATUS.md
    └── RecallInfinity/   → https://github.com/haejoonlim/RecallInfinity
```

## 참고

- **soul-commander · RecallInfinity는 별도 저장소** — 이 저장소에서 커밋·푸시하지 않고 각자 원격에서 관리합니다.
- 작업 공간 내부의 `soul-commander/sprite-workspace/`는 또 다른 별도 저장소(`limagination-workspace` 원격)의 에셋 작업장입니다.
