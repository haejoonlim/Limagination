using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    // P2-4 소환: 미정B 가안 확률 (00 L48) · 130석/회 (00 L25) · 최초 10회 무료 (00 L26) · ★7 제외 (00 L16)
    public class SummonTests
    {
        [SetUp] public void SetUp() { DataLoader.ResetCache(); }

        [Test]
        public void Rank_Table_Matches_Draft_B_And_Never_Rolls_Star7()
        {
            int sum = 0;
            foreach (var w in SummonRules.RankWeightsBp) sum += w;
            Assert.AreEqual(SummonRules.WeightTotalBp, sum);

            Assert.AreEqual(1, SummonSystem.RankFromRoll(0));
            Assert.AreEqual(1, SummonSystem.RankFromRoll(7003));   // 70.04%
            Assert.AreEqual(2, SummonSystem.RankFromRoll(7004));
            Assert.AreEqual(2, SummonSystem.RankFromRoll(9003));   // 20%
            Assert.AreEqual(3, SummonSystem.RankFromRoll(9004));
            Assert.AreEqual(3, SummonSystem.RankFromRoll(9703));   // 7%
            Assert.AreEqual(4, SummonSystem.RankFromRoll(9704));
            Assert.AreEqual(4, SummonSystem.RankFromRoll(9993));   // 2.9%
            Assert.AreEqual(5, SummonSystem.RankFromRoll(9994));
            Assert.AreEqual(5, SummonSystem.RankFromRoll(9998));   // 0.05%
            Assert.AreEqual(6, SummonSystem.RankFromRoll(9999));   // 0.01%

            var rng = new System.Random(7);
            for (int i = 0; i < 100000; i++)
            {
                int r = SummonSystem.RollRank(rng);
                Assert.IsTrue(r >= 1 && r <= 6);
            }
        }

        [Test]
        public void First_10_Free_Then_130_Stones_Each_With_Name_L1()
        {
            var races = DataLoader.LoadRaces().races;
            var d = new SaveData();
            var rng = new System.Random(1);

            for (int i = 0; i < SummonRules.FreeSummons; i++) Assert.IsNotNull(SummonSystem.TrySummon(d, races, rng));
            Assert.AreEqual(10, d.freeSummonsUsed);
            Assert.AreEqual(0, d.soulStones);
            Assert.IsNull(SummonSystem.TrySummon(d, races, rng), "무료 소진 + 석 0");

            d.soulStones = 260;
            Assert.IsNotNull(SummonSystem.TrySummon(d, races, rng));
            Assert.AreEqual(130, d.soulStones);
            Assert.IsNotNull(SummonSystem.TrySummon(d, races, rng));
            Assert.AreEqual(0, d.soulStones);
            Assert.IsNull(SummonSystem.TrySummon(d, races, rng));
            Assert.AreEqual(12, d.totalSummons);
            Assert.AreEqual(12, d.roster.Count);

            foreach (var h in d.roster)
            {
                var race = DataLoader.GetRace(h.raceId);
                Assert.IsNotNull(race, h.raceId);
                CollectionAssert.Contains(race.namePool.examples, h.name, "이름 L1 = namePool.examples");
                Assert.IsTrue(h.rank >= 1 && h.rank <= 6);
            }
        }
    }
}
