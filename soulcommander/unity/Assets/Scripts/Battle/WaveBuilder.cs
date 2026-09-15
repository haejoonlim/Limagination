using System;
using System.Collections.Generic;
using SoulCommander.Data;

namespace SoulCommander.Battle
{
    // monsters.json spawn 기반 적 편성 (02 "전투 편성 층별" 절).
    public static class WaveBuilder
    {
        public const string WaveNormal = "normal";
        public const string WaveBoss = "boss";
        public const string WaveWorld = "world";
        public const int BossMinTier = 4;

        // 03 P2-1: 게이트키퍼 5/10/15/20
        public static readonly int[] GatekeeperFloors = { 5, 10, 15, 20 };

        public static bool IsGatekeeperFloor(int floor) => Array.IndexOf(GatekeeperFloors, floor) >= 0;

        // 일반층: 해당 층이 floors 에 있고 wave 에 "normal"
        public static List<MonsterEntry> NormalPool(IList<MonsterEntry> all, int floor) =>
            Filter(all, floor, m => HasWave(m, WaveNormal));

        // 게이트키퍼층: 해당 층이 floors 에 있고 wave 에 "boss" + tier4 이상
        public static List<MonsterEntry> BossPool(IList<MonsterEntry> all, int floor) =>
            Filter(all, floor, m => HasWave(m, WaveBoss) && m.tier >= BossMinTier);

        // 일반층은 count 체 무작위, 게이트키퍼층은 보스 1체.
        public static List<MonsterEntry> BuildWave(IList<MonsterEntry> all, int floor, int count, Random rng)
        {
            return IsGatekeeperFloor(floor)
                ? Pick(BossPool(all, floor), 1, rng)
                : Pick(NormalPool(all, floor), count, rng);
        }

        // wave 가 ["world"] 뿐인 몬스터 — 전투 웨이브에 절대 안 나옴 (02 L5 규칙)
        public static bool IsWorldOnly(MonsterEntry m)
        {
            var wave = m?.spawn?.wave;
            if (wave == null || wave.Count == 0) return false;
            foreach (var w in wave) if (w != WaveWorld) return false;
            return true;
        }

        // 풀에서 중복 허용 무작위 추출.
        public static List<MonsterEntry> Pick(IList<MonsterEntry> pool, int count, Random rng)
        {
            var wave = new List<MonsterEntry>();
            if (pool == null || pool.Count == 0) return wave;
            for (int i = 0; i < count; i++) wave.Add(pool[rng.Next(pool.Count)]);
            return wave;
        }

        private static bool HasWave(MonsterEntry m, string tag) => m.spawn.wave != null && m.spawn.wave.Contains(tag);

        private static List<MonsterEntry> Filter(IList<MonsterEntry> all, int floor, Predicate<MonsterEntry> extra)
        {
            var pool = new List<MonsterEntry>();
            if (all == null) return pool;
            foreach (var m in all)
            {
                if (m?.spawn?.floors == null || !m.spawn.floors.Contains(floor)) continue;
                if (IsWorldOnly(m)) continue;
                if (!extra(m)) continue;
                pool.Add(m);
            }
            return pool;
        }
    }

    // 보스 스케일 가안 (사용자 승인 2026-09-14): HP·ATK × (배치층 / bossScaleRefFloor). 기준층 이상이면 원본.
    // TODO(P5): 03 P2-1 층 스케일식(+FB-07 −15%) 미정 — 플탐 후 확정
    public static class BossScaling
    {
        public static float Factor(MonsterEntry m, int floor)
        {
            int refFloor = m?.spawn?.bossScaleRefFloor ?? 0;
            if (refFloor <= 0 || floor >= refFloor) return 1f;
            return (float)floor / refFloor;
        }

        public static CombatStats Apply(MonsterEntry m, int floor)
        {
            var s = CombatStats.FromMonster(m);
            float f = Factor(m, floor);
            s.Hp = Math.Max(1, (int)Math.Round(s.Hp * f));
            s.Atk = Math.Max(1, (int)Math.Round(s.Atk * f));
            return s;
        }
    }
}
