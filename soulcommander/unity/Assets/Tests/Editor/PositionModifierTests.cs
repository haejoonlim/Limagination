using NUnit.Framework;
using SoulCommander.Battle;

namespace SoulCommander.Tests
{
    // P2-6 위치보정 (00 L15 #6): 측면+10 / 배후+25 / 고지대+15 / 커버×0.75 — 가산 후 커버 곱
    public class PositionModifierTests
    {
        [Test]
        public void Multipliers_Add_Then_Cover_Multiplies()
        {
            Assert.AreEqual(1.00f, DamageFormula.PositionMultiplier(AttackAngle.Front, false, false), 1e-4f);
            Assert.AreEqual(1.10f, DamageFormula.PositionMultiplier(AttackAngle.Flank, false, false), 1e-4f);
            Assert.AreEqual(1.25f, DamageFormula.PositionMultiplier(AttackAngle.Back, false, false), 1e-4f);
            Assert.AreEqual(1.15f, DamageFormula.PositionMultiplier(AttackAngle.Front, true, false), 1e-4f);
            Assert.AreEqual(1.40f, DamageFormula.PositionMultiplier(AttackAngle.Back, true, false), 1e-4f);
            Assert.AreEqual(0.75f, DamageFormula.PositionMultiplier(AttackAngle.Front, false, true), 1e-4f);
            Assert.AreEqual(1.05f, DamageFormula.PositionMultiplier(AttackAngle.Back, true, true), 1e-4f);
            Assert.AreEqual(0.825f, DamageFormula.PositionMultiplier(AttackAngle.Flank, false, true), 1e-4f);

            Assert.AreEqual(125, DamageFormula.Compute(100, 0, 0f, 1.25f));
            Assert.AreEqual(100, DamageFormula.Compute(100, 0), "기존 호출은 불변");
        }

        [Test]
        public void Angle_Classification_Front_Flank_Back()
        {
            // 대상 (0,0) 이 +X 를 바라봄
            Assert.AreEqual(AttackAngle.Front, Positioning.Classify(0, 0, 1, 0, 5, 0));
            Assert.AreEqual(AttackAngle.Front, Positioning.Classify(0, 0, 1, 0, 5, 3));    // ~31°
            Assert.AreEqual(AttackAngle.Flank, Positioning.Classify(0, 0, 1, 0, 5, 5));    // 45°
            Assert.AreEqual(AttackAngle.Flank, Positioning.Classify(0, 0, 1, 0, 0, 5));    // 90°
            Assert.AreEqual(AttackAngle.Back, Positioning.Classify(0, 0, 1, 0, -5, 5));    // 135°
            Assert.AreEqual(AttackAngle.Back, Positioning.Classify(0, 0, 1, 0, -5, 0));    // 180°
        }

        [Test]
        public void Battle_Applies_Back_Attack_And_Terrain()
        {
            var arena = new ArenaLayout();
            var b = new BattleSystem(1, arena);
            // 적은 -X(다른 쪽)를 바라보고, 영웅은 적 뒤(+X)에서 공격
            var enemy = new BattleUnit { DisplayName = "E", MaxHp = 1000, Hp = 1000, Atk = 1, Def = 0, Aspd = 1, X = 0f, Z = 0f, FacingX = -1f, AttackCooldown = 99f };
            var hero = new BattleUnit { DisplayName = "H", MaxHp = 100, Hp = 100, Atk = 100, Def = 0, Aspd = 10, IsHero = true, X = 2f, Z = 0f, AttackCooldown = 0f };
            b.Heroes.Add(hero);
            b.Enemies.Add(enemy);
            b.Tick(0.01f);
            Assert.AreEqual(1000 - 125, enemy.Hp, "배후 +25%");

            // 영웅 고지대 + 적 커버: (1+0.25+0.15)×0.75 = 1.05 → 105
            arena.Zones.Add(new TerrainZone { Kind = TerrainKind.HighGround, X = 2f, Z = 0f, Radius = 0.5f });
            arena.Zones.Add(new TerrainZone { Kind = TerrainKind.Cover, X = 0f, Z = 0f, Radius = 0.5f });
            enemy.FacingX = -1f;
            hero.AttackCooldown = 0f;
            int before = enemy.Hp;
            b.Tick(0.01f);
            Assert.AreEqual(before - 105, enemy.Hp);
        }
    }
}
