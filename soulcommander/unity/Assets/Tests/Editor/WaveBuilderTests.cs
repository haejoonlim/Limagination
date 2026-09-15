using System.Collections.Generic;
using NUnit.Framework;
using SoulCommander.Battle;
using SoulCommander.Data;

namespace SoulCommander.Tests
{
    // P2-1 층 편성 (02 "전투 편성 층별" · 03 P2-1)
    public class WaveBuilderTests
    {
        [SetUp] public void SetUp() { DataLoader.ResetCache(); }

        [Test]
        public void Floors_1_To_20_Have_Normal_Pools_And_Tier4_Gatekeepers()
        {
            var all = DataLoader.LoadMonsters().monsters;
            CollectionAssert.AreEqual(new[] { 5, 10, 15, 20 }, WaveBuilder.GatekeeperFloors);
            for (int f = 1; f <= 20; f++)
            {
                if (WaveBuilder.IsGatekeeperFloor(f))
                {
                    var bosses = WaveBuilder.BossPool(all, f);
                    Assert.Greater(bosses.Count, 0, $"{f}층 게이트키퍼 없음");
                    foreach (var m in bosses) Assert.GreaterOrEqual(m.tier, 4, $"{f}층 보스 {m.id} tier");
                    Assert.AreEqual(1, WaveBuilder.BuildWave(all, f, 6, new System.Random(f)).Count, $"{f}층 게이트키퍼는 보스 1체");
                }
                else
                {
                    Assert.Greater(WaveBuilder.NormalPool(all, f).Count, 0, $"{f}층 normal 풀 비어있음");
                    foreach (var m in WaveBuilder.BuildWave(all, f, 6, new System.Random(f)))
                        Assert.IsTrue(m.spawn.wave.Contains("normal"), $"{f}층 {m.id} normal 아님");
                }
            }
        }

        [Test]
        public void World_Only_Monsters_Never_Appear_In_Battle_Waves()
        {
            var all = new List<MonsterEntry>(DataLoader.LoadMonsters().monsters);
            var floors = new List<int>();
            for (int f = 1; f <= 100; f++) floors.Add(f);
            // 모든 층·tier4 로 둔 world 전용 몬스터 — 필터가 없으면 일반/보스 풀 양쪽에 들어갈 조건
            var worldOnly = new MonsterEntry
            {
                id = "mon_test_world_only",
                name = "월드 전용(테스트)",
                tier = 4,
                stats = new MonsterStats { hp = 1, atk = 1, def = 0, aspd = 1 },
                spawn = new MonsterSpawn { floors = floors, wave = new List<string> { "world" } },
            };
            all.Add(worldOnly);
            Assert.IsTrue(WaveBuilder.IsWorldOnly(worldOnly));

            var rng = new System.Random(20260914);
            for (int f = 1; f <= 100; f++)
            {
                foreach (var m in WaveBuilder.NormalPool(all, f)) Assert.IsFalse(WaveBuilder.IsWorldOnly(m), $"{f}층 normal 풀에 {m.id}");
                foreach (var m in WaveBuilder.BossPool(all, f)) Assert.IsFalse(WaveBuilder.IsWorldOnly(m), $"{f}층 boss 풀에 {m.id}");
                for (int trial = 0; trial < 30; trial++)
                {
                    foreach (var m in WaveBuilder.BuildWave(all, f, 6, rng))
                    {
                        Assert.IsFalse(WaveBuilder.IsWorldOnly(m), $"{f}층 전투에 world 전용 {m.id} 출현");
                        Assert.AreNotEqual(worldOnly.id, m.id);
                    }
                }
            }
        }

        [Test]
        public void Boss_Scaling_Uses_Ref_Floor()
        {
            var dopp = DataLoader.GetMonster("mon_doppelganger_01");
            Assert.AreEqual(46, dopp.spawn.bossScaleRefFloor);
            var s5 = BossScaling.Apply(dopp, 5);
            Assert.AreEqual(1739, s5.Hp);  // 16000×5/46
            Assert.AreEqual(28, s5.Atk);   // 260×5/46
            Assert.AreEqual(dopp.stats.def, s5.Def);
            Assert.AreEqual(16000, BossScaling.Apply(dopp, 46).Hp, "기준층 이상은 원본");
            Assert.AreEqual(1f, BossScaling.Factor(DataLoader.GetMonster("mon_goblin_01"), 3), "기준층 없는 몬스터는 스케일 없음");
        }
    }
}
