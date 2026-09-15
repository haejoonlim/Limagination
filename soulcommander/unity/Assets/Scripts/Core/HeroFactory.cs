using System.Collections.Generic;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    // 무한 영웅 생성: 종족 균등 랜덤 · 이름은 races.json namePool.examples (이름 L1).
    // 00 L17 (#8): 등급×종족 완전 독립 — 등급은 호출자가 정한다 (소환은 SummonSystem).
    public static class HeroFactory
    {
        public static HeroRecord CreateRandom(IList<RaceEntry> races, System.Random rng) =>
            Create(races, GameRules.StartRank, rng);

        public static HeroRecord Create(IList<RaceEntry> races, int rank, System.Random rng)
        {
            var race = races[rng.Next(races.Count)];
            var names = race.namePool?.examples;
            string name = names != null && names.Count > 0 ? names[rng.Next(names.Count)] : race.name;
            return new HeroRecord
            {
                id = HeroRecord.NewId(),
                name = name,
                raceId = race.id,
                rank = rank,
                level = GameRules.StartLevel,
                personality = Personality.Random(rng), // 01 §4 — 7종 균등 (사용자 결정 2026-09-14)
                job = Job.Common[rng.Next(Job.Common.Length)], // 05 §4 — 공통 8직업 균등 (희귀 직업은 종족 가중치 후속)
            };
        }
    }
}
