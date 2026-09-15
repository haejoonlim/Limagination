using System.Collections.Generic;
using NUnit.Framework;
using SoulCommander.Battle;
using SoulCommander.Core;
using SoulCommander.Data;

namespace SoulCommander.Tests
{
    // P2-5 공명 tier3 (01 §3-2 · races.json resonance)
    public class ResonanceTests
    {
        [SetUp] public void SetUp() { DataLoader.ResetCache(); }

        [Test]
        public void Tier3_Needs_Three_Owned_Of_Same_Lineage()
        {
            var counts = Resonance.CountByLineage(
                new[] { "race_human", "race_genasi", "race_human", "race_woodelf" },
                id => DataLoader.GetRace(id)?.lineage);
            Assert.AreEqual(3, counts["human"]);
            Assert.AreEqual(1, counts["elf"]);
            Assert.AreEqual(1.05f, Resonance.HpAtkMultiplier(counts, "human"), 1e-4f);
            Assert.AreEqual(1f, Resonance.HpAtkMultiplier(counts, "elf"), 1e-4f);

            // tier5/7 은 구조만 — HP/ATK 보정은 tier3 의 +5% 그대로 (CP 합산 금지)
            var many = new Dictionary<string, int> { { "beast", 5 }, { "dwarf", 7 } };
            Assert.AreEqual(5, Resonance.Tier(many, "beast"));
            Assert.AreEqual(7, Resonance.Tier(many, "dwarf"));
            Assert.AreEqual(1.05f, Resonance.HpAtkMultiplier(many, "dwarf"), 1e-4f);
        }

        [Test]
        public void Applies_To_Sortie_Members_And_Recalculates_On_Death()
        {
            var b = new BattleSystem();
            var baseStats = new HeroBaseStats { hp = 500, atk = 45, def = 20, aspd = 10, mag = 20, mana = 100, spd_cast = 30, sta = 80 };
            var h1 = b.AddHero("h1", "A", DataLoader.GetRace("race_human"), baseStats, 1, 1);
            var h2 = b.AddHero("h2", "B", DataLoader.GetRace("race_genasi"), baseStats, 1, 1);
            var elf = b.AddHero("h3", "C", DataLoader.GetRace("race_woodelf"), baseStats, 1, 1);

            // 보유 human 3명 (1명은 출격하지 않음) → 출격한 human 계열 2명에게만 적용
            b.SetOwnedLineageCounts(new Dictionary<string, int> { { "human", 3 }, { "elf", 1 } });
            Assert.AreEqual(525, h1.MaxHp);
            Assert.AreEqual(47, h1.Atk);
            Assert.AreEqual(525, h2.MaxHp);
            Assert.AreEqual(500, elf.MaxHp);
            Assert.AreEqual(45, elf.Atk);

            // 전투 중 사망 → 보유 2명 → tier3 해제
            h2.Hp = 0;
            b.HandleHeroDeath(h2);
            Assert.AreEqual(500, h1.MaxHp);
            Assert.AreEqual(45, h1.Atk);
        }
    }
}
