using System;
using System.Collections.Generic;

namespace SoulCommander.Core
{
    // 수집 공명 (races.json resonance · 01 §3-2).
    // 판정 = 보유(소유) 기준 · 적용 = 출격 멤버 · 전투 중 사망 시 재계산 (resonance.note).
    public static class Resonance
    {
        // tier3: 동계열 3명 보유 → 출격한 해당 계열 HP/ATK +5%
        public const int Tier3Count = 3;
        public const float Tier3HpAtkBonus = 0.05f;

        // tier5(계열 패시브)·tier7(궁극기 +20%)은 구조만 — CP 합산 금지 (01 §3-2). 효과 미적용.
        public const int Tier5Count = 5;
        public const int Tier7Count = 7;

        public static Dictionary<string, int> CountByLineage(IEnumerable<string> ownedRaceIds, Func<string, string> lineageOf)
        {
            var counts = new Dictionary<string, int>();
            foreach (var raceId in ownedRaceIds)
            {
                var lineage = lineageOf(raceId);
                if (string.IsNullOrEmpty(lineage)) continue;
                counts.TryGetValue(lineage, out int n);
                counts[lineage] = n + 1;
            }
            return counts;
        }

        public static int Tier(IReadOnlyDictionary<string, int> counts, string lineage)
        {
            if (lineage == null || counts == null || !counts.TryGetValue(lineage, out int n)) return 0;
            if (n >= Tier7Count) return 7;
            if (n >= Tier5Count) return 5;
            if (n >= Tier3Count) return 3;
            return 0;
        }

        public static float HpAtkMultiplier(IReadOnlyDictionary<string, int> counts, string lineage) =>
            Tier(counts, lineage) >= 3 ? 1f + Tier3HpAtkBonus : 1f;
    }
}
