using NUnit.Framework;
using SoulCommander.Battle;

namespace SoulCommander.Tests
{
    // v8.0 확정 데미지 공식.
    public class DamageFormulaTests
    {
        [Test]
        public void Def_Zero_Deals_Full_Atk()
        {
            Assert.AreEqual(100, DamageFormula.Compute(100, 0));
        }

        [Test]
        public void Def_200_Halves_Damage()
        {
            // DEF/(DEF+200) = 0.5 → 100*(1-0.5)=50
            Assert.AreEqual(50, DamageFormula.Compute(100, 200));
        }

        [Test]
        public void Def_20_Against_Atk_45()
        {
            // 20/(20+200) = 0.0909... → 45*(1-0.0909)=40.9 → round=41
            Assert.AreEqual(41, DamageFormula.Compute(45, 20));
        }

        [Test]
        public void Minimum_Damage_Is_One()
        {
            Assert.AreEqual(1, DamageFormula.Compute(1, 100000));
        }

        [Test]
        public void Penetration_Reduces_Effective_Def()
        {
            // pen=0.5, def=100 → effDef=50 → 100*(1-50/250)=100*0.8=80
            Assert.AreEqual(80, DamageFormula.Compute(100, 100, 0.5f));
        }

        [Test]
        public void Full_Penetration_Ignores_Def()
        {
            Assert.AreEqual(100, DamageFormula.Compute(100, 500, 1f));
        }

        [Test]
        public void Zero_Atk_Deals_Zero()
        {
            Assert.AreEqual(0, DamageFormula.Compute(0, 20));
        }
    }
}
