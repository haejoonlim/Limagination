using System.Collections.Generic;
using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    // P3-4·P3-5: 01 §3 CP 공식 + 성격(§4)·상태(§5)·공명(tier3) 반영
    public class CombatPowerTests
    {
        private static readonly HeroBaseStats Base = new HeroBaseStats
        {
            hp = 500, atk = 45, def = 20, aspd = 10, mag = 20,
            mdef = 0, pen = 0, eva = 0, cdmg = 0, cri = 0,
            mana = 100, spd_cast = 30, sta = 80
        };

        [SetUp] public void SetUp() { DataLoader.ResetCache(); }

        [Test]
        public void StatScore_Growth_And_Compute_Follow_Section3()
        {
            // 01 §3 13종: 500*0.12 + 45*2 + 20*2 + 20*1.5 + 10*3 + 30*2 + 100*0.05 + 80*0.03
            var s = new StatBlock { Hp = 500, Atk = 45, Def = 20, Aspd = 10, Mag = 20, Mana = 100, SpdCast = 30, Sta = 80 };
            Assert.AreEqual(317.4f, CombatPower.StatScore(s), 1e-3f);
            Assert.AreEqual(317.4f, CombatPower.Growth(s, 1, 1), 1e-2f);
            Assert.AreEqual(1177.554f, CombatPower.Growth(s, 6, 1), 1e-2f);      // ★6 ×3.71
            Assert.AreEqual(1533.042f, CombatPower.Growth(s, 7, 1), 1e-2f);     // ★7 ×4.83
            Assert.AreEqual(476.1f, CombatPower.Growth(s, 1, 11), 1e-2f);       // Lv11 ×1.5 (가안 곡선)

            Assert.AreEqual(300, CombatPower.Compute(200f, 50f, 50f, 1f, 1f, 1f), "(G + E + K)");
            Assert.AreEqual(260, CombatPower.Compute(250f, 0f, 0f, 1.04f, 1f, 1f));
            // 범위: P 0.95~1.10 · C 0.80~1.10 · R 1.00~1.10
            Assert.AreEqual(110, CombatPower.Compute(100f, 0f, 0f, 1.5f, 1f, 1f));
            Assert.AreEqual(80, CombatPower.Compute(100f, 0f, 0f, 1f, 0.5f, 1f));
            Assert.AreEqual(100, CombatPower.Compute(100f, 0f, 0f, 1f, 1f, 0.9f));

            Assert.AreEqual(1 + 2 + 3 + 5 + 8, Skills.Score(new List<int> { Skills.Common, Skills.Rare, Skills.Heroic, Skills.Legendary, Skills.Mythic }));
            Assert.AreEqual(0, Skills.Score(new List<int>()), "스킬 슬롯 구조만 — 기본 K=0");
        }

        [Test]
        public void Personality_Seven_Types_Random_Assignment()
        {
            Assert.AreEqual(7, Personality.Keys.Length);
            Assert.AreEqual(1.03f, Personality.Multiplier("brave"), 1e-4f);
            Assert.AreEqual(1.02f, Personality.Multiplier("careful"), 1e-4f);
            Assert.AreEqual(1.02f, Personality.Multiplier("cool"), 1e-4f);
            Assert.AreEqual(1.04f, Personality.Multiplier("berserk"), 1e-4f);
            Assert.AreEqual(1.00f, Personality.Multiplier("devoted"), 1e-4f, "헌신 — 힐러 개념 전까지 1.00");
            Assert.AreEqual(1.02f, Personality.Multiplier("cunning"), 1e-4f);
            Assert.AreEqual(1.00f, Personality.Multiplier("neutral"), 1e-4f);
            Assert.AreEqual(1.00f, Personality.Multiplier("unknown"), 1e-4f);

            var rng = new System.Random(3);
            var seen = new HashSet<string>();
            for (int i = 0; i < 500; i++)
            {
                var k = Personality.Random(rng);
                CollectionAssert.Contains(Personality.Keys, k);
                seen.Add(k);
            }
            Assert.AreEqual(7, seen.Count, "7종 균등 랜덤");
        }

        [Test]
        public void State_Correction_Adds_Then_Clamps()
        {
            Assert.AreEqual(1.00f, StateCorrection.Multiplier(0, 0, 100), 1e-4f);
            Assert.AreEqual(1.05f, StateCorrection.Multiplier(1, 0, 100), 1e-4f, "사기 높음 +5%");
            Assert.AreEqual(0.95f, StateCorrection.Multiplier(-1, 0, 100), 1e-4f, "사기 낮음 −5%");
            Assert.AreEqual(0.95f, StateCorrection.Multiplier(0, 1, 100), 1e-4f, "스트레스 높음 −5%");
            Assert.AreEqual(0.90f, StateCorrection.Multiplier(0, 2, 100), 1e-4f, "스트레스 한계 −10%");
            Assert.AreEqual(1.00f, StateCorrection.Multiplier(0, 0, 50), 1e-4f);
            Assert.AreEqual(0.95f, StateCorrection.Multiplier(0, 0, 49), 1e-4f, "Sanity 경고 <50");
            Assert.AreEqual(0.90f, StateCorrection.Multiplier(0, 0, 24), 1e-4f, "Sanity 위험 <25");
            Assert.AreEqual(0.95f, StateCorrection.Multiplier(1, 1, 45), 1e-4f, "가산: 1 + 0.05 − 0.05 − 0.05");
            Assert.AreEqual(0.80f, StateCorrection.Multiplier(-1, 2, 10), 1e-4f, "0.75 → 하한 0.80");
        }

        [Test]
        public void Hero_Cp_Reflects_Personality_State_Resonance_Equipment()
        {
            var human = DataLoader.GetRace("race_human");
            var none = new Dictionary<string, int>();

            var plain = new HeroRecord { id = "n", raceId = "race_human", rank = 1, level = 1, personality = "neutral" };
            Assert.AreEqual(317, HeroPower.Compute(plain, human, Base, default, none).Cp);

            // 성격 광폭 1.04 × 사기 높음 1.05 → 346
            var h = new HeroRecord { id = "a", raceId = "race_human", rank = 1, level = 1, personality = "berserk", morale = 1, sanity = 100 };
            var c = HeroPower.Compute(h, human, Base, default, none);
            Assert.AreEqual(1.04f, c.P, 1e-4f);
            Assert.AreEqual(1.05f, c.C, 1e-4f);
            Assert.AreEqual(1.00f, c.R, 1e-4f);
            Assert.AreEqual(347, c.Cp);

            // 공명 tier3 (human 보유 3) R 1.05 → 364
            var owned = new Dictionary<string, int> { { "human", 3 } };
            Assert.AreEqual(364, HeroPower.Compute(h, human, Base, default, owned).Cp);

            // Sanity 위험 → C = 1 + 0.05 − 0.10 = 0.95 → 314
            h.sanity = 20;
            Assert.AreEqual(314, HeroPower.Compute(h, human, Base, default, none).Cp);

            // 장비 E: ATK 5 → E 10 → 327
            Assert.AreEqual(327, HeroPower.Compute(plain, human, Base, new StatBlock { Atk = 5 }, none).Cp);

            Assert.AreEqual("CP 12,400 (유효 ~12,400)", HeroPower.Format(12400));
        }

        [Test]
        public void Party_Cp_Sums_Sortie_And_Applies_Owned_Resonance()
        {
            var d = new SaveData();
            var a = new HeroRecord { id = "a", name = "A", raceId = "race_human", rank = 1, level = 11, personality = "neutral" };
            var b = new HeroRecord { id = "b", name = "B", raceId = "race_genasi", rank = 1, level = 11, personality = "neutral" };
            d.roster.Add(a);
            d.roster.Add(b);
            d.party.Add("a");
            d.party.Add("b");

            var counts = Resonance.CountByLineage(new[] { "race_human", "race_genasi" }, id => DataLoader.GetRace(id)?.lineage);
            Assert.AreEqual(952, HeroPower.PartyCp(d, counts), "476 × 2 (공명 없음)");

            // 출격 안 하는 human 1명 추가 보유 → human 계열 3 → 출격 2명 R 1.05 → 500 × 2
            d.roster.Add(new HeroRecord { id = "c", name = "C", raceId = "race_human", rank = 1, level = 1, personality = "neutral" });
            counts = Resonance.CountByLineage(new[] { "race_human", "race_genasi", "race_human" }, id => DataLoader.GetRace(id)?.lineage);
            Assert.AreEqual(1000, HeroPower.PartyCp(d, counts));
        }

        [Test]
        public void Recommended_Cp_Is_Enemy_Lineup_Score()
        {
            var all = DataLoader.LoadMonsters().monsters;
            // 1층: monsters.json mdef+aspd 반영 → 평균 79.0 × 6체 = 474
            Assert.AreEqual(474, RecommendedPower.ForFloor(all, 1, 6));
            // 5층 게이트키퍼: 도플갱어 스케일 HP1739·ATK28·DEF45·MDEF80·ASPD7 → 473
            Assert.AreEqual(473, RecommendedPower.ForFloor(all, 5, 6));
        }

        [Test]
        public void Star7_Transcendence_Is_Structure_Only()
        {
            var h = new HeroRecord { id = "s6", rank = 6 };
            Assert.IsTrue(Transcendence.IsEligibleRank(h));
            Assert.IsFalse(Transcendence.CanTranscend(h), "미정C — 비활성");
            Assert.IsFalse(Transcendence.TryTranscend(h));
            Assert.AreEqual(6, h.rank);
            Assert.IsFalse(Transcendence.IsEligibleRank(new HeroRecord { rank = 5 }));
        }
    }
}
