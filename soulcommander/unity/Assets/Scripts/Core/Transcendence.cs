using SoulCommander.Save;

namespace SoulCommander.Core
{
    // ★7 초월진화 — 구조만 (03 P3-2). 00 L16 (#7): ★7 은 초월진화 전용 · 계수 ×4.83 (01 §2).
    // TODO(P5): 조건·재료·단계 미정C (00 L39) — 확정 전까지 전부 비활성
    public static class Transcendence
    {
        public const int FromRank = 6;
        public const int ToRank = 7;
        public const string DisabledReason = "초월진화 조건 미정 (미정C)";

        public static readonly bool Enabled = false;

        public static bool IsEligibleRank(HeroRecord h) => h != null && h.rank == FromRank;

        public static bool CanTranscend(HeroRecord h) => Enabled && IsEligibleRank(h);

        // 조건 확정 전에는 항상 실패 — 등급을 바꾸지 않는다.
        public static bool TryTranscend(HeroRecord h)
        {
            if (!CanTranscend(h)) return false;
            h.rank = ToRank;
            return true;
        }
    }
}
