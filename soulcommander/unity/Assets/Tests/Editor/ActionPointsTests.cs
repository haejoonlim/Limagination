using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    // 00 L14 (#5): MAX30 · 처치+1 · 일반2/게이트3 · 초과분 소멸
    public class ActionPointsTests
    {
        [Test]
        public void Entry_Deducts_And_Kills_Cap_At_Max()
        {
            var d = new SaveData();
            Assert.AreEqual(30, d.ap, "초기 AP = 30");

            Assert.IsTrue(ActionPoints.TrySpendForEntry(d, gatekeeperFloor: false));
            Assert.AreEqual(28, d.ap, "일반층 진입 -2");

            for (int i = 0; i < 5; i++) ActionPoints.OnKill(d);
            Assert.AreEqual(30, d.ap, "처치 +1 이지만 MAX 30 초과분 소멸");

            d.ap = 3;
            Assert.IsTrue(ActionPoints.TrySpendForEntry(d, gatekeeperFloor: true));
            Assert.AreEqual(0, d.ap, "게이트키퍼 진입 -3");

            d.ap = 1;
            Assert.IsFalse(ActionPoints.TrySpendForEntry(d, gatekeeperFloor: false), "AP 부족 시 진입 불가");
            Assert.AreEqual(1, d.ap, "실패 시 차감 없음");
        }
    }

    // 00 L31 (#19): 퇴장층×30석 + 게이트잭팟(게이트층²×1,000) · 골드 층×100 (00 L29 #22)
    public class RunRewardsTests
    {
        [Test]
        public void Normal_Floor_Pays_Floor_Multiples_Without_Jackpot()
        {
            var r = RunRewards.ForFloor(3);
            Assert.AreEqual(300, r.Gold);
            Assert.AreEqual(90, r.SoulStones);
            Assert.AreEqual(0, r.Jackpot, "일반층 잭팟 없음");
            Assert.AreEqual(240, r.Exp);
        }

        [Test]
        public void Gate_Floor_Adds_FloorSq_Jackpot()
        {
            var r = RunRewards.ForFloor(5);
            Assert.AreEqual(500, r.Gold);
            Assert.AreEqual(150, r.SoulStones);
            Assert.AreEqual(25 * 1000, r.Jackpot, "게이트층²×1,000");
            Assert.AreEqual(400, r.Exp);

            var d = new SaveData();
            RunRewards.Settle(d, 10);
            Assert.AreEqual(300 + 100_000, d.soulStones, "정산 시 석 + 잭팟 합산 지급");
            Assert.AreEqual(1000, d.gold);
        }
    }
}
