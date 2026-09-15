using System;

namespace SoulCommander.Core
{
    // 레벨계수 가안: 1 + (Lv−1) × 0.05 → Lv100 ×5.95. 00 L23 (#14): 전 등급 Lv100.
    // D-172 곡선식 미제공 — 현행 유지 (사용자 결정 2026-09-14). 레벨업 필요 경험치는 미구현.
    // TODO(P5): D-172 곡선 확정 시 교체
    public static class LevelCurve
    {
        public const int MaxLevel = 100;
        public const float PerLevel = 0.05f;

        public static float Multiplier(int level)
        {
            int lv = Math.Max(1, Math.Min(MaxLevel, level));
            return 1f + (lv - 1) * PerLevel;
        }
    }
}
