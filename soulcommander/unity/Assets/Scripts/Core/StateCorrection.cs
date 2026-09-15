using System;

namespace SoulCommander.Core
{
    // 01 §5 상태보정 C — 가산 후 클램프 [0.80, 1.10] (사용자 결정 2026-09-14).
    // 사기(식당·추모)·스트레스(숙소)는 영지 전 단계라 영웅별 수동 설정값. 영지 페이즈에서 자동 연결.
    public static class StateCorrection
    {
        public const int MoraleLow = -1, MoraleNormal = 0, MoraleHigh = 1;
        public const int StressNormal = 0, StressHigh = 1, StressLimit = 2;

        // 01 §5
        public const float MoraleHighBonus = 0.05f;
        public const float MoraleLowPenalty = -0.05f;
        public const float StressHighPenalty = -0.05f;
        public const float StressLimitPenalty = -0.10f;
        public const float SanityWarningPenalty = -0.05f;
        public const float SanityDangerPenalty = -0.10f;

        // TODO(P5): Sanity 구간 경계 가안 — 경고 <50 · 위험 <25
        public const int SanityWarningBelow = 50;
        public const int SanityDangerBelow = 25;

        public static float MoraleTerm(int morale) =>
            morale >= MoraleHigh ? MoraleHighBonus : morale <= MoraleLow ? MoraleLowPenalty : 0f;

        public static float StressTerm(int stress) =>
            stress >= StressLimit ? StressLimitPenalty : stress == StressHigh ? StressHighPenalty : 0f;

        public static float SanityTerm(int sanity) =>
            sanity < SanityDangerBelow ? SanityDangerPenalty : sanity < SanityWarningBelow ? SanityWarningPenalty : 0f;

        public static float Multiplier(int morale, int stress, int sanity) =>
            CombatPower.Clamp(1f + MoraleTerm(morale) + StressTerm(stress) + SanityTerm(sanity),
                CombatPower.StateMin, CombatPower.StateMax);

        public static int ClampMorale(int v) => Math.Max(MoraleLow, Math.Min(MoraleHigh, v));
        public static int ClampStress(int v) => Math.Max(StressNormal, Math.Min(StressLimit, v));

        public static string MoraleName(int v) => v >= MoraleHigh ? "높음" : v <= MoraleLow ? "낮음" : "보통";
        public static string StressName(int v) => v >= StressLimit ? "한계" : v == StressHigh ? "높음" : "보통";
        public static string SanityBand(int v) => v < SanityDangerBelow ? "위험" : v < SanityWarningBelow ? "경고" : "정상";
    }
}
