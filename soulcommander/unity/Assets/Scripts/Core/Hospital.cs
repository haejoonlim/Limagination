using System;
using System.Collections.Generic;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 병원: 생존자 Sanity 요양만 — 부활 없음 (00 L13 #4).
    // 수치는 가안 (사용자 결정 2026-09-14): 시작 100 · 전투 참가 -5 · 아군 사망 목격 -10/명.
    // 병상·회복량은 04 §3.10 병원 L1 (병상 2 · Sanity 회복 +10).
    // TODO(P5): Sanity 손실·회복 수치 확정. 효과(01 §5 경고 -5% / 위험 -10%)는 P3-5.
    public static class Hospital
    {
        public const int SanityMax = 100;
        public const int SanityStart = 100;
        public const int BattleParticipationLoss = 5;
        public const int AllyDeathWitnessLoss = 10;
        public const int Beds = 2;           // 04 §3.10 병원 L1
        public const int RestRecovery = 10;  // 04 §3.10 병원 L1

        public static int StressFor(int allyDeaths) => BattleParticipationLoss + AllyDeathWitnessLoss * Math.Max(0, allyDeaths);

        // 전투에서 살아남은 참가자에게 스트레스 적용
        public static void ApplyBattleStress(SaveData d, IEnumerable<string> survivorIds, int allyDeaths)
        {
            int loss = StressFor(allyDeaths);
            foreach (var id in survivorIds)
            {
                var h = d.roster.Find(x => x.id == id);
                if (h != null) h.sanity = Math.Max(0, h.sanity - loss);
            }
        }

        // 허브 복귀 요양: Sanity 낮은 순으로 병상 수만큼 회복. 요양받은 영웅을 돌려준다.
        public static List<HeroRecord> Rest(SaveData d)
        {
            var candidates = d.roster.FindAll(h => h.sanity < SanityMax);
            candidates.Sort((a, b) => a.sanity.CompareTo(b.sanity));
            if (candidates.Count > Beds) candidates.RemoveRange(Beds, candidates.Count - Beds);
            foreach (var h in candidates) h.sanity = Math.Min(SanityMax, h.sanity + RestRecovery);
            return candidates;
        }
    }
}
