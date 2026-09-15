using NUnit.Framework;
using SoulCommander.Battle;

namespace SoulCommander.Tests
{
    // P2-3 전술개입: 게이지 최대100·시작50·초당+2·처치+10 (AGENTS §4) · 1~3층 완전자동
    public class TacticalGaugeTests
    {
        [Test]
        public void Floors_1_To_3_Auto_And_Floor_4_Gauge_Spec()
        {
            for (int f = 1; f <= 3; f++)
            {
                var auto = new TacticalGauge(f);
                Assert.IsFalse(auto.Enabled, $"{f}층은 완전자동");
                Assert.IsFalse(auto.TrySpend(1f));
            }

            var g = new TacticalGauge(4);
            Assert.IsTrue(g.Enabled);
            Assert.AreEqual(50f, g.Value, 1e-4f);
            g.Tick(5f);
            Assert.AreEqual(60f, g.Value, 1e-4f, "초당 +2");
            g.OnKill();
            Assert.AreEqual(70f, g.Value, 1e-4f, "처치 +10");
            g.Tick(100f);
            g.OnKill();
            Assert.AreEqual(100f, g.Value, 1e-4f, "최대 100");
        }

        [Test]
        public void Commands_Move_20_Focus_30_Only_From_Floor_4()
        {
            var b = new BattleSystem(4, null);
            var hero = new BattleUnit { DisplayName = "H", MaxHp = 100, Hp = 100, Atk = 10, Aspd = 10, IsHero = true };
            var enemy = new BattleUnit { DisplayName = "E", MaxHp = 100, Hp = 100, Atk = 10, Aspd = 10, X = 3f };
            b.Heroes.Add(hero);
            b.Enemies.Add(enemy);

            Assert.IsTrue(b.CommandFocus(enemy));
            Assert.AreEqual(20f, b.Gauge.Value, 1e-4f);
            Assert.AreSame(enemy, b.FocusTarget);
            Assert.IsTrue(b.CommandMove(hero, 1f, 2f));
            Assert.AreEqual(0f, b.Gauge.Value, 1e-4f);
            Assert.IsTrue(hero.HasMoveTarget);
            Assert.IsFalse(b.CommandFocus(enemy), "게이지 부족");
            Assert.IsFalse(b.CommandFocus(hero), "아군은 집중 대상 아님");

            var early = new BattleSystem(3, null);
            var h3 = new BattleUnit { DisplayName = "H3", MaxHp = 100, Hp = 100, IsHero = true };
            early.Heroes.Add(h3);
            Assert.IsFalse(early.CommandMove(h3, 0f, 0f), "3층 이하는 명령 불가");
        }
    }
}
