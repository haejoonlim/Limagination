using System.Collections.Generic;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 소환 ★1~★6 (00 L16 #7 — ★7 은 초월진화 전용이라 뽑기 제외).
    // 00 L17 (#8): 등급×종족 완전 독립 · 중복 허용 · 템플릿 강제 없음 (01 §1).
    public static class SummonRules
    {
        // 00 L25 (#16): 영혼석(하) 130개당 1회 (티켓 130석)
        public const int StoneCost = 130;
        // 00 L26 (#17): 최초 10회 무료
        public const int FreeSummons = 10;

        // 00 L48 미정B 가안 (합 100%): ★1 70.04% · ★2 20% · ★3 7% · ★4 2.9% · ★5 0.05% · ★6 0.01%
        // 만분율(합 10000 · 1bp = 0.01%). TODO(P5): 확률표 확정 — 미정B (00 L38)
        public static readonly int[] RankWeightsBp = { 7004, 2000, 700, 290, 5, 1 };
        public const int WeightTotalBp = 10000;

        // TODO(P5): 천장(★4/★5/★6) — 미정A (00 L37). 미구현.
    }

    public static class SummonSystem
    {
        // roll: 0 ~ 9999 → ★1~★6
        public static int RankFromRoll(int roll)
        {
            int acc = 0;
            for (int i = 0; i < SummonRules.RankWeightsBp.Length; i++)
            {
                acc += SummonRules.RankWeightsBp[i];
                if (roll < acc) return i + 1;
            }
            return SummonRules.RankWeightsBp.Length;
        }

        public static int RollRank(System.Random rng) => RankFromRoll(rng.Next(SummonRules.WeightTotalBp));

        public static bool IsNextFree(SaveData d) => d.freeSummonsUsed < SummonRules.FreeSummons;

        public static bool CanSummon(SaveData d) => IsNextFree(d) || d.soulStones >= SummonRules.StoneCost;

        // 성공 시 roster 에 추가된 영웅, 석 부족이면 null.
        public static HeroRecord TrySummon(SaveData d, IList<RaceEntry> races, System.Random rng)
        {
            if (!CanSummon(d)) return null;
            if (IsNextFree(d)) d.freeSummonsUsed++;
            else d.soulStones -= SummonRules.StoneCost;
            d.totalSummons++;

            var hero = HeroFactory.Create(races, RollRank(rng), rng);
            d.roster.Add(hero);
            return hero;
        }
    }
}
