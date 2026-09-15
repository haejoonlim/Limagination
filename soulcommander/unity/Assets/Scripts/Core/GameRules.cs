namespace SoulCommander.Core
{
    // 확정 수치 모음. "00 Lnn" = design-docs/GDD_v8.0_00_확정사항.md 의 줄 번호.
    public static class GameRules
    {
        // 00 L14 (#5): AP MAX30 · 처치+1 · 시간회복없음 · 일반2/게이트3
        public const int MaxAp = 30;
        public const int StartAp = MaxAp;
        public const int ApPerKill = 1;
        public const int ApCostNormalFloor = 2;
        public const int ApCostGateFloor = 3;

        // 00 L31 (#19): 퇴장 시 퇴장층×30석 + 게이트잭팟(게이트층²×1,000). 식민섬은 석 수급에 배율 없음.
        // TODO(P5): 지급식 계수 튜닝·식민섬 계수 — 미정G (00 L40)
        public const int SoulStonesPerFloor = 30;
        public const int GateJackpotPerFloorSq = 1000;

        // 골드 = 층×100×(1+0.2×식민섬수) (00 L29 #22). 식민섬 미구현(0개) → 배율 1.
        // 경험치: 00 에 해당 행 없음 — AGENTS §4 경제 · 04 §3.11 · 03 P1-3 근거
        public const int GoldPerFloor = 100;
        public const int ExpPerFloor = 80;

        // 일반층 적 편성 수 — 00 미등재 가안. TODO(P5): 층 스케일식 (03 P2-1)
        public const int EnemiesPerWave = 6;

        // 03 P2-1: 1~20층 (게이트키퍼 판정은 WaveBuilder.GatekeeperFloors)
        public const int MaxFloor = 20;

        // 00 L16 (#7) / 01 §2: ★1 ×1.00 기준. 00 L23 (#14): 전 등급 Lv100
        public const int StartRank = 1;
        public const int StartLevel = 1;
    }
}
