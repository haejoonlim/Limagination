# Limagination

> **We Begin with Imagination.**
> 호기심이 우리의 시작이다. 상상이 우리의 언어다.

Limagination의 브랜드 자산과 Unity 게임 스크립트를 모은 공식 저장소입니다.

## 구조

```
├── brand/
│   ├── LIMAGINATION_BRAND_CONSTITUTION.txt   # 브랜드 헌장 v2.0
│   ├── LIMAGINATION_BRANDING_REPORT.txt      # 브랜딩 리포트
│   └── logo.png                              # 브랜드 이미지
└── unity-scripts/
    ├── CharacterPartComposer.cs              # 캐릭터/몬스터 무한 생성기
    │                                         #   (조건부 가중치 파츠 조합, Unity)
    └── WFCDungeonGenerator.cs                # WAVE Function Collapse 기반
                                              #   던전 타일 생성기 (Unity)
```

## Unity 스크립트

| 스크립트 | 설명 |
|---|---|
| `CharacterPartComposer.cs` | 조건부 가중치 기반 파츠 조합으로 캐릭터/몬스터를 절차적으로 생성 |
| `WFCDungeonGenerator.cs` | Wave Function Collapse 알고리즘으로 던전 맵을 절차적 생성 |

두 스크립트 모두 Unity (C#)용이며 독립적으로 동작합니다.
