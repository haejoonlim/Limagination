using System.Collections.Generic;
using System.Globalization;
using SoulCommander.Battle;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Core
{
    public struct CpBreakdown
    {
        public float G, E, K, P, C, R;
        public int Cp;
    }

    // 01 §3 ④ 스킬 — 슬롯 구조만. 스킬 데이터·획득은 후속 (사용자 결정 2026-09-14). K = 희귀도 점수 합.
    public static class Skills
    {
        public const int Common = 0, Rare = 1, Heroic = 2, Legendary = 3, Mythic = 4;

        public static int Score(List<int> rarities)
        {
            if (rarities == null) return 0;
            int sum = 0;
            var pts = CombatPower.SkillRarityPoints;
            foreach (var r in rarities) sum += pts[System.Math.Max(0, System.Math.Min(pts.Length - 1, r))];
            return sum;
        }
    }

    // 영웅 CP = round((G + E + K) × P × C × R) — 01 §3
    public static class HeroPower
    {
        public static CpBreakdown Compute(HeroRecord h, RaceEntry race, HeroBaseStats baseStats, StatBlock equipment,
                                          IReadOnlyDictionary<string, int> ownedByLineage)
        {
            var b = new CpBreakdown();
            if (h == null || baseStats == null) return b;
            b.G = CombatPower.Growth(CombatPower.RaceBase(race, baseStats), h.rank, h.level);
            b.E = CombatPower.StatScore(equipment);
            b.K = Skills.Score(h.skillRarities);
            b.P = Personality.Multiplier(h.personality);
            b.C = StateCorrection.Multiplier(h.morale, h.stress, h.sanity);
            b.R = Resonance.HpAtkMultiplier(ownedByLineage, race?.lineage); // R 은 tier3 만 (01 §3-2)
            b.Cp = CombatPower.Compute(b.G, b.E, b.K, b.P, b.C, b.R);
            return b;
        }

        public static CpBreakdown Compute(SaveData d, HeroRecord h, IReadOnlyDictionary<string, int> ownedByLineage) =>
            Compute(h, DataLoader.GetRace(h.raceId), DataLoader.GetHeroBaseStats(),
                EquipmentSystem.EquippedStats(d, DataLoader.LoadEquipment(), h.id), ownedByLineage);

        // 파티CP = 출격 5명 합산 (01 §3)
        public static int PartyCp(SaveData d, IReadOnlyDictionary<string, int> ownedByLineage)
        {
            int sum = 0;
            foreach (var h in Party.Members(d)) sum += Compute(d, h, ownedByLineage).Cp;
            return sum;
        }

        // 유효CP 가안: 지형 상성 데이터가 생길 때까지 날것과 동일 (2026-09-14). TODO(P5)
        public static int EffectiveCp(int rawCp) => rawCp;

        // 표시: `CP 12,400 (유효 ~12,400)` — 01 §3 표기 (지형 라벨은 상성 데이터 후속)
        public static string Format(int rawCp) => $"CP {N(rawCp)} (유효 ~{N(EffectiveCp(rawCp))})";

        public static string N(int v) => v.ToString("N0", CultureInfo.InvariantCulture);
    }

    // 권장CP 가안 (2026-09-14): 해당 층 적 편성의 ①식 점수 합 × 1.0. 게이트키퍼는 보스 스케일 반영.
    // 입장 제한 없음 (01 §3). TODO(P5): 계수 튜닝 (01 "플탐에서 볼 것" 3)
    public static class RecommendedPower
    {
        public const float Factor = 1.0f;

        public static int ForFloor(IList<MonsterEntry> all, int floor, int enemiesPerWave)
        {
            if (WaveBuilder.IsGatekeeperFloor(floor))
            {
                var bosses = WaveBuilder.BossPool(all, floor);
                if (bosses.Count == 0) return 0;
                float sum = 0f;
                foreach (var m in bosses) sum += Score(BossScaling.Apply(m, floor));
                return (int)System.Math.Round(sum / bosses.Count * Factor);
            }
            var pool = WaveBuilder.NormalPool(all, floor);
            if (pool.Count == 0) return 0;
            float total = 0f;
            foreach (var m in pool) total += Score(CombatStats.FromMonster(m));
            return (int)System.Math.Round(total / pool.Count * enemiesPerWave * Factor);
        }

        // 몬스터 JSON 에는 13종 중 일부만 존재하므로 없는 항은 0
        public static float Score(CombatStats s) =>
            CombatPower.StatScore(new StatBlock
            {
                Hp = s.Hp, Atk = s.Atk, Mag = s.Mag, Def = s.Def, MDef = s.MDef, Aspd = s.Aspd
            });
    }
}
