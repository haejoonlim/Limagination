using System;
using NUnit.Framework;
using SoulCommander.Core;
using SoulCommander.Data;
using SoulCommander.Save;

namespace SoulCommander.Tests
{
    // P3-3 장비 최소 세트 가안 (equipment.json) · 03 P1-4 사망 시 장비반환
    public class EquipmentTests
    {
        [SetUp] public void SetUp() { DataLoader.ResetCache(); }

        [Test]
        public void Shop_Equip_Enhance_And_Death_Returns_Gear()
        {
            var eq = DataLoader.LoadEquipment();
            Assert.AreEqual(9, eq.equipment.Count, "3슬롯 × 3등급");

            var d = new SaveData { gold = 1000 };
            var hero = new HeroRecord { id = "h", name = "H", raceId = "race_human", rank = 1, level = 1 };
            d.roster.Add(hero);

            var sword = EquipmentSystem.Buy(d, eq, "eq_weapon_1");
            Assert.IsNotNull(sword);
            Assert.AreEqual(800, d.gold, "하급 200G");
            Assert.IsNull(EquipmentSystem.Buy(d, eq, "eq_weapon_3"), "상급 2000G — 골드 부족");
            Assert.AreEqual(800, d.gold);

            Assert.IsTrue(EquipmentSystem.Equip(d, eq, sword.uid, "h"));
            Assert.AreEqual(5, EquipmentSystem.EquippedStats(d, eq, "h").Atk);

            var armor = EquipmentSystem.Buy(d, eq, "eq_armor_1");
            EquipmentSystem.Equip(d, eq, armor.uid, "h");
            Assert.IsTrue(EquipmentSystem.TryEnhance(d, eq, armor), "+1 비용 100");
            Assert.IsTrue(EquipmentSystem.TryEnhance(d, eq, armor), "+2 비용 200");
            Assert.AreEqual(300, d.gold);
            var st = EquipmentSystem.EquippedStats(d, eq, "h");
            Assert.AreEqual(48, st.Hp, "40 × 1.2");
            Assert.AreEqual(5, st.Def, "4 × 1.2 = 4.8 → 5");

            // 같은 슬롯에 새 장비 → 기존 장비는 보관함으로
            var sword2 = EquipmentSystem.Buy(d, eq, "eq_weapon_1");
            Assert.IsTrue(EquipmentSystem.Equip(d, eq, sword2.uid, "h"));
            Assert.IsTrue(string.IsNullOrEmpty(sword.equippedBy));
            Assert.AreEqual(1, EquipmentSystem.FreeItemsForSlot(d, eq, "weapon").Count);

            // 사망 → 장착 장비 2개 반환
            var entry = Permadeath.RecordDeath(d, hero, 2, "고블린", DateTime.UtcNow);
            Assert.AreEqual(2, entry.returnedEquipment);
            Assert.AreEqual(3, d.inventory.Count, "장비는 사라지지 않고 보관함에 남는다");
            foreach (var it in d.inventory) Assert.IsTrue(string.IsNullOrEmpty(it.equippedBy));

            // 강화 상한 +10
            armor.enhance = eq.meta.enhanceMax;
            d.gold = 99999;
            Assert.IsFalse(EquipmentSystem.TryEnhance(d, eq, armor));
        }
    }
}
